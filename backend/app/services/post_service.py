"""Service de posts."""

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.core.logging_config import get_logger
from app.oauth.oauth_client import XOAuthClient
from app.models.enums import (
    PostAccountStatus,
    PostStatus,
)
from app.models.post import Post
from app.models.post_account import PostAccount
from app.models.post_media import PostMedia
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_media_repository import PostMediaRepository
from app.repositories.post_repository import PostRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.services.base_service import (
    BaseService,
    NotFoundError,
    ValidationError,
)
from app.core import media_storage
from app.core.crypto import decrypt_token, encrypt_token
from app.core.exceptions import BaseAppException, ConflictException
from app.domain.content_invariants import has_duplicates, preserves_invariants
from app.domain.media_rules import (
    MAX_MEDIA_PER_POST,
    validate_media_combination,
    x_media_category_for,
)
from app.domain.policies import MANDATORY_VARIATION_ACCOUNT_THRESHOLD
from app.domain.post_composition import find_accounts_missing_independent_text
from app.domain.publication_cost import credits_per_account_for_post
from app.models.enums import PostCompositionMode
from app.services.jitter_service import JitterService

logger = get_logger(__name__)


class PostService(BaseService[Post]):
    def __init__(
        self,
        post_repository: PostRepository,
        post_account_repository: PostAccountRepository,
        twitter_account_repository: TwitterAccountRepository,
        user_repository: UserRepository,
        x_oauth_client: XOAuthClient,
        subscription_service: SubscriptionService,
        post_media_repository: PostMediaRepository,
        jitter_service: JitterService,
    ) -> None:
        super().__init__(post_repository)
        self.post_repository = post_repository
        self.post_account_repository = post_account_repository
        self.twitter_account_repository = twitter_account_repository
        self.user_repository = user_repository
        self.x_oauth_client = x_oauth_client
        self.subscription_service = subscription_service
        self.post_media_repository = post_media_repository
        self.jitter_service = jitter_service
        # Mesma sessao usada pelos repositories acima (todos compartilham
        # a sessao vinda de `get_db`/`SessionLocal`). Guardada aqui para
        # que `publish_post` possa commitar imediatamente apos cada
        # efeito externo bem-sucedido -- ver docstring de `publish_post`.
        self.db = post_repository.db

    def list_all_posts(
        self,
        *,
        status: PostStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Post]:
        """Posts de todos os usuarios (visao administrativa) -- ver
        `GET /admin/posts`. Nao filtra por dono de proposito."""
        return self.post_repository.list_all(status=status, offset=offset, limit=limit)

    def list_user_posts(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Post]:
        self._ensure_user_exists(user_id)
        return self.post_repository.list_by_user(user_id, offset=offset, limit=limit)

    def list_user_posts_by_status(
        self,
        user_id: uuid.UUID,
        status: PostStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Post]:
        self._ensure_user_exists(user_id)
        return self.post_repository.list_by_user_and_status(
            user_id, status, offset=offset, limit=limit
        )

    def count_by_status(self, status: PostStatus) -> int:
        return self.post_repository.count_by_status(status)

    def get_post(
        self,
        post_id: uuid.UUID,
    ) -> Post:
        return self.ensure_exists(
            post_id,
            message="Post nao encontrado.",
        )

    def delete_post(
        self,
        post_id: uuid.UUID,
    ) -> None:
        post = self.ensure_exists(
            post_id,
            message="Post nao encontrado.",
        )

        # Correcao (auditoria funcional): protege a integridade do
        # historico de publicacoes. O frontend ja escondia o botao
        # "Excluir" para `Post.status == "published"`, mas essa e a
        # condicao do status AGREGADO -- um post com falha PARCIAL
        # (`Post.status == FAILED` com, por exemplo, 2 de 3 contas
        # PUBLISHED) nao era barrado nem no frontend nem aqui no
        # backend. `PostAccountStatus.PUBLISHED` e tratado como
        # terminal/protegido em todo o resto do sistema (nunca
        # reprocessado por retries -- ver `publish_post`); excluir o
        # `Post` apagaria em cascata (`Post.post_accounts`,
        # cascade="all, delete-orphan") o unico registro que o XHub
        # mantem de uma publicacao que de fato aconteceu no X
        # (`x_post_id`), mesmo o tweet continuando publicado la. Reforcado
        # aqui -- unica fonte de verdade real, independente do que o
        # frontend mostra ou de chamadas diretas a API.
        if any(
            post_account.status == PostAccountStatus.PUBLISHED
            for post_account in self.post_account_repository.list_by_post(post_id)
        ):
            raise ConflictException(
                "Este post ja foi publicado em pelo menos uma conta e nao "
                "pode mais ser excluido."
            )

        # A linha de PostMedia e removida em cascata pelo banco (ver
        # `Post.media`, cascade="all, delete-orphan" + FK ON DELETE
        # CASCADE), mas o arquivo em disco precisa ser apagado
        # explicitamente ANTES -- SQLAlchemy/Postgres nao sabem tocar o
        # filesystem.
        for media_item in self.post_media_repository.list_by_post(post_id):
            media_storage.delete_file(media_item.storage_path)

        self.post_repository.delete(post)

    def create_post(
        self,
        *,
        user_id: uuid.UUID,
        twitter_account_ids: Sequence[uuid.UUID],
        composition_mode: PostCompositionMode = PostCompositionMode.SHARED,
        text: str | None = None,
        rendered_texts: Mapping[uuid.UUID, str] | None = None,
        media_ids: Sequence[uuid.UUID] | None = None,
        account_media_ids: Mapping[uuid.UUID, Sequence[uuid.UUID]] | None = None,
    ) -> Post:
        """Cria um `Post` e um `PostAccount` por conta selecionada, num
        dos dois modos de composicao (ver
        `app.models.enums.PostCompositionMode`, CLAUDE.md e
        docs/ROADMAP_COMPOSICAO_POST.md):

        - SHARED (Fluxo 1, comportamento historico, default): `text` e
          obrigatorio e vira `Post.text`. `rendered_texts` (Publicacao
          Inteligente -- ver docs/ROADMAP_PUBLICACAO_INTELIGENTE.md) e
          um mapa OPCIONAL de `twitter_account_id -> texto final
          aprovado`; ausente, `PostAccount.rendered_text` fica `NULL` e
          `publish_post` usa `Post.text`. `media_ids` (ver
          docs/ROADMAP_MEDIA.md) e IDENTICA para todas as contas.
        - INDEPENDENT (Fluxo 2): nao existe texto principal -- `text`
          deve vir vazio/ausente, e `Post.text` fica `NULL`.
          `rendered_texts` passa a ser OBRIGATORIO para TODA conta
          selecionada (cada uma com seu proprio tweet, sem relacao
          entre si -- nunca invariantes preservadas, nunca variacao por
          IA). Midia pode ser compartilhada (`media_ids`, mesmo
          comportamento do modo SHARED) OU individual por conta
          (`account_media_ids`, mapa `twitter_account_id -> media_ids`)
          -- nunca as duas ao mesmo tempo.
        """
        self._ensure_user_exists(user_id)

        if not twitter_account_ids:
            raise ValidationError("Selecione ao menos uma conta do X.")

        if len(set(twitter_account_ids)) != len(twitter_account_ids):
            raise ValidationError(
                "twitter_account_ids nao pode conter ids duplicados."
            )

        for account_id in twitter_account_ids:
            account = self.twitter_account_repository.get(account_id)

            if account is None:
                raise NotFoundError("Conta do X nao encontrada.")

            if account.user_id != user_id:
                raise NotFoundError("Conta do X nao pertence ao usuario.")

        if media_ids and account_media_ids:
            raise ValidationError(
                "Escolha midia compartilhada ou midia por conta, nao as "
                "duas ao mesmo tempo."
            )

        if composition_mode is PostCompositionMode.INDEPENDENT:
            if text is not None and text.strip():
                raise ValidationError(
                    "No modo de conteudo independente por conta nao "
                    "existe texto principal -- envie apenas o texto de "
                    "cada conta."
                )

            unknown_ids = set((rendered_texts or {}).keys()) - set(twitter_account_ids)
            if unknown_ids:
                raise ValidationError(
                    "rendered_texts contem contas que nao fazem parte "
                    "de twitter_account_ids."
                )

            missing = find_accounts_missing_independent_text(
                twitter_account_ids, rendered_texts
            )
            if missing:
                raise ValidationError(
                    "No modo de conteudo independente por conta, toda "
                    "conta selecionada precisa ter seu proprio texto."
                )

            for account_text in (rendered_texts or {}).values():
                if len(account_text) > 280:
                    raise ValidationError(
                        "O texto de uma das contas excede o limite de "
                        "280 caracteres."
                    )

            shared_media_items = self._validate_and_load_media(
                user_id=user_id, media_ids=media_ids
            )
            account_media_items = self._validate_and_load_account_media(
                user_id=user_id,
                account_media_ids=account_media_ids,
                twitter_account_ids=twitter_account_ids,
            )
            post_text = None
        else:
            if not text or not text.strip():
                raise ValidationError("O texto do post nao pode estar vazio.")

            if account_media_ids:
                raise ValidationError(
                    "Midia por conta so esta disponivel no modo de "
                    "conteudo independente por conta."
                )

            shared_media_items = self._validate_and_load_media(
                user_id=user_id, media_ids=media_ids
            )
            account_media_items = {}

            self._validate_rendered_texts(
                text=text,
                twitter_account_ids=twitter_account_ids,
                rendered_texts=rendered_texts,
            )
            post_text = text.strip()

            if rendered_texts:
                variation_count = sum(
                    1 for account_id in twitter_account_ids if rendered_texts.get(account_id)
                )
                logger.info(
                    "Post confirmado com textos finais da Publicacao "
                    "Inteligente (conteudo omitido do log).",
                    extra={
                        "account_count": len(twitter_account_ids),
                        "accounts_with_final_text": variation_count,
                    },
                )

        post = self.post_repository.create(
            {
                "user_id": user_id,
                "text": post_text,
                "status": PostStatus.PENDING,
                "composition_mode": composition_mode,
            }
        )

        post_accounts_by_id: dict[uuid.UUID, PostAccount] = {}
        for account_id in twitter_account_ids:
            rendered_text = (
                rendered_texts.get(account_id) if rendered_texts else None
            )
            post_accounts_by_id[account_id] = self.post_account_repository.create(
                {
                    "post_id": post.id,
                    "twitter_account_id": account_id,
                    "rendered_text": (
                        rendered_text.strip() if rendered_text else None
                    ),
                }
            )

        for position, media_item in enumerate(shared_media_items):
            self.post_media_repository.attach_to_post(
                media_item, post_id=post.id, position=position
            )

        for account_id, media_items in account_media_items.items():
            post_account = post_accounts_by_id[account_id]
            for position, media_item in enumerate(media_items):
                self.post_media_repository.attach_to_post(
                    media_item,
                    post_id=post.id,
                    position=position,
                    post_account_id=post_account.id,
                )

        return post

    def _validate_and_load_media(
        self,
        *,
        user_id: uuid.UUID,
        media_ids: Sequence[uuid.UUID] | None,
    ) -> list[PostMedia]:
        """Valida `media_ids` (ver docs/ROADMAP_MEDIA.md) ANTES de criar
        o `Post`: cada midia deve pertencer ao usuario, ainda nao estar
        anexada a nenhum outro post, e a combinacao de tipos deve
        respeitar as regras oficiais do X (ex.: video nao pode ser
        combinado com outras midias). Retorna os `PostMedia` na MESMA
        ordem recebida -- essa ordem vira `position` no attach."""
        if not media_ids:
            return []

        if len(media_ids) > MAX_MEDIA_PER_POST:
            raise ValidationError(
                f"Um post pode ter no maximo {MAX_MEDIA_PER_POST} arquivos de midia."
            )

        if len(set(media_ids)) != len(media_ids):
            raise ValidationError("media_ids nao pode conter ids duplicados.")

        found = self.post_media_repository.list_by_ids_and_user(media_ids, user_id)
        found_by_id = {media.id: media for media in found}

        missing = [media_id for media_id in media_ids if media_id not in found_by_id]
        if missing:
            raise NotFoundError(
                "Uma ou mais midias nao foram encontradas, nao pertencem "
                "ao usuario ou ja foram anexadas a outro post."
            )

        media_items = [found_by_id[media_id] for media_id in media_ids]

        combination_error = validate_media_combination(
            [media.media_type.value for media in media_items]
        )
        if combination_error:
            raise ValidationError(combination_error)

        return media_items

    def _validate_and_load_account_media(
        self,
        *,
        user_id: uuid.UUID,
        account_media_ids: Mapping[uuid.UUID, Sequence[uuid.UUID]] | None,
        twitter_account_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, list[PostMedia]]:
        """Midia individual por conta (modo INDEPENDENT, midia NAO
        compartilhada -- ver `PostService.create_post`). Cada conta e
        validada com as MESMAS regras de `_validate_and_load_media`
        (pertence ao usuario, ainda nao anexada, combinacao de tipos
        valida), como um post independente em si. Alem disso, a MESMA
        midia nao pode aparecer em duas contas diferentes desta
        requisicao -- sem essa checagem, as duas passariam na validacao
        individual (nenhuma das duas ainda anexada) e o attach
        posterior faria a segunda conta "roubar" silenciosamente a
        midia da primeira."""
        if not account_media_ids:
            return {}

        unknown_ids = set(account_media_ids.keys()) - set(twitter_account_ids)
        if unknown_ids:
            raise ValidationError(
                "account_media_ids contem contas que nao fazem parte "
                "de twitter_account_ids."
            )

        all_media_ids: list[uuid.UUID] = [
            media_id
            for media_ids in account_media_ids.values()
            for media_id in media_ids
        ]
        if len(set(all_media_ids)) != len(all_media_ids):
            raise ValidationError(
                "Uma midia nao pode ser usada em mais de uma conta."
            )

        return {
            account_id: self._validate_and_load_media(
                user_id=user_id, media_ids=media_ids
            )
            for account_id, media_ids in account_media_ids.items()
        }

    def _validate_rendered_texts(
        self,
        *,
        text: str,
        twitter_account_ids: Sequence[uuid.UUID],
        rendered_texts: Mapping[uuid.UUID, str] | None,
    ) -> None:
        """Publicacao Inteligente -- valida os textos finais por conta
        antes de criar o `Post`.

        Regras oficiais aplicadas aqui (ver roadmap):
        - Nenhum texto final pode ser vazio ou exceder o limite de
          caracteres do post.
        - Edicao manual/variacao nunca pode alterar URLs, hashtags,
          @mencoes ou emojis presentes no texto original (elementos
          imutaveis).
        - Com 5 ou mais contas selecionadas, a geracao de variacoes e
          OBRIGATORIA: todas as contas devem ter um `rendered_text`
          valido e distinto entre si -- nunca o mesmo texto publicado
          em varias contas. Sem isso, a criacao do post e recusada
          ANTES de qualquer chamada ao X.
        """
        if rendered_texts:
            unknown_ids = set(rendered_texts.keys()) - set(twitter_account_ids)
            if unknown_ids:
                raise ValidationError(
                    "rendered_texts contem contas que nao fazem parte "
                    "de twitter_account_ids."
                )

            for account_id, rendered_text in rendered_texts.items():
                if not rendered_text or not rendered_text.strip():
                    raise ValidationError(
                        "O texto final de cada conta nao pode estar vazio."
                    )

                if len(rendered_text) > 280:
                    raise ValidationError(
                        "O texto final de uma das contas excede o limite "
                        "de 280 caracteres."
                    )

                if not preserves_invariants(text, rendered_text):
                    raise ValidationError(
                        "O texto final de uma das contas altera links, "
                        "hashtags, @mencoes ou emojis do texto original, "
                        "o que nao e permitido."
                    )

        if len(twitter_account_ids) >= MANDATORY_VARIATION_ACCOUNT_THRESHOLD:
            provided = rendered_texts or {}

            missing = [
                account_id
                for account_id in twitter_account_ids
                if not provided.get(account_id)
            ]
            if missing:
                raise ValidationError(
                    "Com 5 ou mais contas selecionadas, a Publicacao "
                    "Inteligente e obrigatoria: gere e revise as "
                    "variacoes antes de criar o post."
                )

            final_texts = [provided[account_id] for account_id in twitter_account_ids]
            if has_duplicates(final_texts):
                raise ValidationError(
                    "Com 5 ou mais contas selecionadas, o mesmo texto nao "
                    "pode ser publicado em mais de uma conta. Gere "
                    "variacoes validas antes de continuar."
                )

    def publish_post(self, post_id: uuid.UUID) -> Post:
        """Publica um post em todas as contas do X vinculadas a ele.

        Regras:
        1. Idempotencia: `PostAccount` cujo status ja e PUBLISHED nunca
           e reprocessado -- nao ha nova chamada a API do X para ele,
           evitando publicacao duplicada em reprocessamentos/retries.
        2. Nenhuma chamada a API do X (efeito externo irreversivel)
           acontece antes de TODAS as validacoes de negocio (assinatura
           ativa + saldo de posts suficiente para a quantidade de
           contas que efetivamente serao publicadas nesta chamada)
           serem aprovadas. A validacao e feita com a linha de
           `Subscription` travada (`FOR UPDATE`) para fechar a janela
           de corrida entre checar e consumir saldo.
        3. Correcao critica (auditoria item 5 -- dessincronizacao entre
           o efeito externo e o banco): antes desta correcao, o estado
           PUBLISHED de cada `PostAccount` so era persistido no commit
           unico feito pela ROTA, ao final de toda a funcao. Se o
           processo morresse (crash, OOM, timeout de worker) depois que
           o X ja aceitou o tweet mas antes desse commit final, a
           publicacao ficava "perdida" do ponto de vista do banco
           (rollback implicito) mesmo tendo acontecido de verdade no X
           -- um retry subsequente publicaria o mesmo texto de novo,
           duplicado, na conta real do cliente.
           Agora, cada `PostAccount` e commitado individualmente e
           IMEDIATAMENTE apos sua chamada a API do X ser respondida
           (sucesso ou falha) e o consumo de saldo correspondente ser
           aplicado -- nunca antes da chamada externa. Isso reduz a
           janela de inconsistencia ao minimo necessario (a fracao de
           segundo entre a resposta do X e o `COMMIT` local) e, mais
           importante, preserva a garantia de idempotencia do item 1:
           mesmo que o processo morra logo em seguida, o que ja foi
           commitado nao sera reprocessado, e o que ainda nao foi
           commitado nunca chegou a ter efeito externo.
        4. Jitter (ver docs/ROADMAP_JITTER.md): entre uma publicacao e a
           proxima (nunca antes da primeira, nunca se so houver uma
           conta pendente), aguarda um atraso aleatorio independente
           (`JitterService.apply_delay`) para que a sequencia de
           chamadas a API do X pareca menos automatizada. Nao afeta
           nenhuma das garantias acima -- e apenas um `time.sleep`
           entre iteracoes do mesmo loop, antes de qualquer efeito
           colateral da proxima conta (token, midia, publicacao).
        5. Reuso de conexao HTTP (analise de escalabilidade -- ver
           claude.md): `self.x_oauth_client` e a MESMA instancia de
           `XOAuthClient` para todas as contas deste post, reaproveitando
           um unico `httpx.Client`/pool de conexoes keep-alive com
           `api.x.com` em vez de abrir uma conexao TCP/TLS nova por
           chamada -- relevante para posts com muitas contas. Fechado no
           `finally` abaixo, ja que esta e a ultima operacao que usa essa
           instancia dentro desta chamada.
        6. Custo por conta (ver docs/ROADMAP_CUSTO_LINK.md): um post cujo
           `Post.text` contenha pelo menos um link consome
           `LINK_CREDITS_PER_ACCOUNT` (15) creditos por conta publicada
           com sucesso, em vez do `DEFAULT_CREDITS_PER_ACCOUNT` (1) usado
           para qualquer outro post (texto simples ou com midia
           anexada). Calculado uma unica vez a partir do texto original
           (`app.domain.publication_cost.credits_per_account_for_post`)
           e usado tanto na validacao de saldo suficiente ANTES de
           qualquer chamada ao X quanto no consumo efetivo apos cada
           conta publicada -- nunca um valor fixo de 1, e nunca
           validado com um custo diferente do que sera de fato
           consumido.
        """
        try:
            return self._publish_post(post_id)
        finally:
            self.x_oauth_client.close()

    def _publish_post(self, post_id: uuid.UUID) -> Post:
        post = self.post_repository.get(post_id)

        if post is None:
            raise NotFoundError("Post nao encontrado.")

        post_accounts = self.post_account_repository.list_by_post(post_id)

        accounts_to_publish = self.post_account_repository.list_pending_or_failed_by_post_for_update_skip_locked(
            post_id
        )

        if not accounts_to_publish:
            if any(
                post_account.status != PostAccountStatus.PUBLISHED
                for post_account in post_accounts
            ):
                raise ConflictException(
                    "Post ja esta sendo publicado por outra requisicao."
                )

            post = self.post_repository.update(
                post,
                {
                    "status": PostStatus.PUBLISHED
                    if not any(
                        account.status == PostAccountStatus.FAILED
                        for account in post_accounts
                    )
                    else PostStatus.FAILED
                },
            )
            self.db.commit()
            return post

        if accounts_to_publish:
            # Publicacao Inteligente -- defesa em profundidade (ver
            # docs/ROADMAP_PUBLICACAO_INTELIGENTE.md, fluxo de
            # publicacao: "valida regra obrigatoria de 5+ contas antes
            # do envio ao X"). `PostService.create_post` ja recusa
            # criar um post de 5+ contas sem variacoes validas e
            # distintas, mas esta checagem re-valida o estado
            # persistido no banco imediatamente antes de qualquer
            # chamada externa -- protege contra edicoes diretas no
            # banco, dados de uma versao anterior da aplicacao, ou
            # qualquer outro caminho que tenha contornado a validacao
            # de criacao. Nunca publica o mesmo texto em 2+ das contas
            # sendo enviadas nesta chamada quando a regra se aplica.
            # A obrigatoriedade de variacao distinta em 5+ contas e uma
            # regra exclusiva da Publicacao Inteligente (modo SHARED) --
            # nao existe "original" nem "variacao" no modo INDEPENDENT
            # (Fluxo 2), onde cada conta ja e um texto proprio e
            # independente por definicao (duplicar texto entre contas e
            # permitido, e uma decisao manual do usuario).
            if (
                post.composition_mode is PostCompositionMode.SHARED
                and len(post_accounts) >= MANDATORY_VARIATION_ACCOUNT_THRESHOLD
            ):
                all_effective_texts = [
                    post_account.rendered_text or post.text
                    for post_account in post_accounts
                ]
                pending_effective_texts = [
                    post_account.rendered_text or post.text
                    for post_account in accounts_to_publish
                ]
                if any(
                    not text.strip() for text in pending_effective_texts
                ) or has_duplicates(all_effective_texts):
                    raise ValidationError(
                        "Este post tem 5 ou mais contas e exige variacoes "
                        "validas e distintas por conta antes da "
                        "publicacao. Gere as variacoes novamente antes de "
                        "tentar publicar."
                    )

            # Custo por conta (ver docs/ROADMAP_CUSTO_LINK.md): posts com
            # link no texto consomem `LINK_CREDITS_PER_ACCOUNT` (15)
            # creditos por conta publicada; qualquer outro post (texto
            # simples ou com midia anexada) continua consumindo 1,
            # comportamento identico ao anterior a esta regra. Calculado
            # a partir do texto EFETIVO de cada conta (`rendered_text or
            # post.text`) -- no modo SHARED isso sempre da o mesmo
            # resultado para todas as contas (toda variacao preserva
            # exatamente os links do original, `preserves_invariants`
            # descarta qualquer variacao que adicione ou remova um
            # link), mas no modo INDEPENDENT cada conta tem seu proprio
            # texto e pode ter um custo diferente das demais.
            credits_by_post_account_id = {
                post_account.id: credits_per_account_for_post(
                    post_account.rendered_text or post.text
                )
                for post_account in accounts_to_publish
            }

            # Validacao completa de negocio ANTES de qualquer chamada
            # externa. Se a assinatura nao existir, estiver inativa ou
            # sem saldo suficiente para todas as contas pendentes (na
            # soma dos custos por conta calculados acima), nenhuma
            # publicacao ocorre e a excecao sobe para a rota (que faz
            # rollback -- nada e alterado).
            subscription = self.subscription_service.ensure_can_publish(
                post.user_id,
                required_posts=sum(credits_by_post_account_id.values()),
            )

            for account_index, post_account in enumerate(accounts_to_publish):
                # Jitter (ver docs/ROADMAP_JITTER.md): atraso aleatorio
                # aplicado ENTRE publicacoes em contas diferentes deste
                # post, nunca antes da primeira. So existe "entre" a
                # partir da segunda conta do LOTE sendo publicado nesta
                # chamada (`accounts_to_publish`, ja excluindo contas
                # PUBLISHED anteriormente) -- se so houver uma conta
                # pendente, `account_index` nunca passa de 0 e nenhum
                # atraso e aplicado, satisfazendo a regra "se existir
                # apenas uma conta: nao aplicar atraso" sem precisar de
                # uma checagem separada de `len(accounts_to_publish)`.
                if account_index > 0:
                    self.jitter_service.apply_delay(
                        post_id=post_id,
                        account_index=account_index,
                        total_accounts=len(accounts_to_publish),
                    )

                twitter_account = self.twitter_account_repository.get(
                    post_account.twitter_account_id
                )

                if twitter_account is None:
                    self._mark_post_account_failed(
                        post_account,
                        error_message="Conta do X nao encontrada.",
                    )
                    self.db.commit()
                    continue

                try:
                    access_token = self._get_valid_access_token(twitter_account)

                    # Publicacao Inteligente: publica o texto final
                    # aprovado para ESTA conta (variacao gerada por IA
                    # ou edicao manual) quando existir; caso contrario,
                    # o texto original do post -- comportamento
                    # identico ao anterior a esta funcionalidade.
                    text_to_publish = post_account.rendered_text or post.text

                    # Midia (ver docs/ROADMAP_MEDIA.md e
                    # app.models.enums.PostCompositionMode): a
                    # compartilhada entre todas as contas mais a
                    # exclusiva DESTA conta, se houver (modo
                    # INDEPENDENT com midia individualizada) -- cada
                    # conta do X tem seu proprio access_token/biblioteca
                    # de midia, entao o arquivo precisa ser enviado ao X
                    # uma vez POR CONTA, imediatamente antes de criar o
                    # tweet desta conta. Falha no upload de midia cai
                    # nos mesmos handlers de excecao abaixo (marca este
                    # PostAccount como FAILED, nunca publica o texto sem
                    # a midia esperada).
                    media_for_account = self.post_media_repository.list_for_post_account(
                        post_id=post.id, post_account_id=post_account.id
                    )
                    x_media_ids = [
                        self.x_oauth_client.upload_media(
                            access_token=access_token,
                            file_path=media_storage.resolve_path(media_item.storage_path),
                            content_type=media_item.content_type,
                            media_category=x_media_category_for(media_item.media_type.value),
                            total_bytes=media_item.file_size_bytes,
                        )
                        for media_item in media_for_account
                    ]

                    published_post = self.x_oauth_client.publish_post(
                        access_token=access_token,
                        text=text_to_publish,
                        media_ids=x_media_ids or None,
                    )

                    # O tweet ja existe de verdade no X neste ponto --
                    # marcamos e commitamos PUBLISHED imediatamente,
                    # antes de qualquer outra operacao, para que nenhum
                    # erro subsequente (ex.: consumo de saldo) possa
                    # fazer este `PostAccount` ser rotulado como FAILED
                    # apesar da publicacao ter, de fato, acontecido.
                    self._mark_post_account_published(
                        post_account,
                        x_post_id=published_post.post_id,
                    )
                    self.db.commit()

                except BaseAppException as exc:
                    self.db.rollback()
                    self._mark_post_account_failed(
                        post_account,
                        error_message=exc.message,
                    )
                    self.db.commit()
                    logger.warning(
                        "Falha esperada ao publicar post_account.",
                        extra={
                            "post_id": str(post_id),
                            "post_account_id": str(post_account.id),
                            "error": exc.message,
                        },
                    )
                    continue
                except Exception as exc:  # noqa: BLE001
                    # Falha inesperada (rede, timeout, bug) -- nao deve
                    # derrubar o processamento das demais contas do
                    # post nem vazar como 500 sem rastro (auditoria
                    # item 4). Registrada com stacktrace completo e o
                    # post_account correspondente e marcado como FAILED
                    # para que o usuario possa tentar republicar.
                    self.db.rollback()
                    self._mark_post_account_failed(
                        post_account,
                        error_message="Erro inesperado ao publicar no X.",
                    )
                    self.db.commit()
                    logger.exception(
                        "Falha inesperada ao publicar post_account.",
                        extra={
                            "post_id": str(post_id),
                            "post_account_id": str(post_account.id),
                        },
                    )
                    continue

                try:
                    # A capacidade ja foi validada acima (para todas as
                    # `accounts_to_publish`, na soma de
                    # `credits_by_post_account_id`); o consumo efetivo
                    # por conta publicada com sucesso mantem `used_posts`
                    # correto mesmo se parte das contas falhar -- cada
                    # conta bem-sucedida consome exatamente o credito
                    # calculado PARA ELA (1 ou 15, ver calculo acima),
                    # nunca um valor fixo nem o de outra conta.
                    self.subscription_service.consume_posts(
                        subscription.id,
                        credits_by_post_account_id[post_account.id],
                    )
                    self.db.commit()
                except BaseAppException:
                    # O tweet ja foi publicado (e ja esta commitado como
                    # PUBLISHED acima) -- nao revertemos isso. Uma
                    # falha aqui significa apenas que o saldo da
                    # assinatura nao pode ser decrementado (ex.: corrida
                    # rara envolvendo outra publicacao concorrente).
                    # Registramos como erro critico para investigacao
                    # administrativa em vez de perder o rastro
                    # silenciosamente.
                    self.db.rollback()
                    logger.error(
                        "Post publicado no X mas saldo da assinatura "
                        "nao pode ser consumido -- requer verificacao "
                        "administrativa.",
                        extra={
                            "post_id": str(post_id),
                            "post_account_id": str(post_account.id),
                            "subscription_id": str(subscription.id),
                        },
                    )

        # Recarrega o estado mais recente (as contas podem ter sido
        # commitadas individualmente acima).
        post_accounts = self.post_account_repository.list_by_post(post_id)

        has_failure = any(
            post_account.status == PostAccountStatus.FAILED
            for post_account in post_accounts
        )

        post = self.post_repository.update(
            post,
            {"status": (PostStatus.FAILED if has_failure else PostStatus.PUBLISHED)},
        )
        self.db.commit()

        logger.info(
            "Processamento de publicacao concluido.",
            extra={
                "post_id": str(post_id),
                "status": post.status.value,
            },
        )

        return post

    def _get_valid_access_token(self, twitter_account) -> str:
        now = datetime.now(UTC)
        expires_at = twitter_account.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at <= now:
            tokens = self.x_oauth_client.refresh_access_token(
                refresh_token=decrypt_token(twitter_account.refresh_token),
            )
            self.twitter_account_repository.update(
                twitter_account,
                {
                    "access_token": encrypt_token(tokens.access_token),
                    "refresh_token": encrypt_token(tokens.refresh_token),
                    "expires_at": tokens.expires_at,
                },
            )
            # Commit imediato e independente: o token renovado deve ser
            # persistido assim que obtido, sem depender do resultado da
            # publicacao que vem a seguir. Muitos provedores OAuth (X
            # incluso) rotacionam o refresh_token a cada uso -- se este
            # commit nao acontecesse aqui e um rollback() posterior (ex.:
            # falha ao publicar) desfizesse esta atualizacao, o refresh
            # token antigo (ja invalidado pelo X) ficaria salvo no banco,
            # quebrando todas as tentativas futuras de renovacao.
            self.db.commit()
            return tokens.access_token

        return decrypt_token(twitter_account.access_token)
    def _mark_post_account_published(
        self,
        post_account,
        *,
        x_post_id: str,
    ) -> None:

        self.post_account_repository.update(
            post_account,
            {
                "status": PostAccountStatus.PUBLISHED,
                "published_at": datetime.now(UTC),
                "x_post_id": x_post_id,
                "error_message": None,
            },
        )

    def _mark_post_account_failed(
        self,
        post_account,
        *,
        error_message: str,
    ) -> None:
        self.post_account_repository.update(
            post_account,
            {
                "status": PostAccountStatus.FAILED,
                "error_message": error_message,
            },
        )

    def _ensure_user_exists(self, user_id: uuid.UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError("Usuario nao encontrado.")

    def _ensure_post_exists(self, post_id: uuid.UUID) -> None:
        if self.post_repository.get(post_id) is None:
            raise NotFoundError("Post nao encontrado.")
