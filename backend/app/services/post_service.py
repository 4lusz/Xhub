"""Service de posts."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.logging_config import get_logger
from app.oauth.oauth_client import XOAuthClient
from app.models.enums import (
    PostAccountStatus,
    PostStatus,
)
from app.models.post import Post
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_repository import PostRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.services.base_service import (
    BaseService,
    NotFoundError,
    ValidationError,
)
from app.core.crypto import decrypt_token, encrypt_token
from app.core.exceptions import BaseAppException

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
    ) -> None:
        super().__init__(post_repository)
        self.post_repository = post_repository
        self.post_account_repository = post_account_repository
        self.twitter_account_repository = twitter_account_repository
        self.user_repository = user_repository
        self.x_oauth_client = x_oauth_client
        self.subscription_service = subscription_service
        # Mesma sessao usada pelos repositories acima (todos compartilham
        # a sessao vinda de `get_db`/`SessionLocal`). Guardada aqui para
        # que `publish_post` possa commitar imediatamente apos cada
        # efeito externo bem-sucedido -- ver docstring de `publish_post`.
        self.db = post_repository.db

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

        self.post_repository.delete(post)

    def create_post(
        self,
        *,
        user_id: uuid.UUID,
        text: str,
        twitter_account_ids: Sequence[uuid.UUID],
    ) -> Post:
        self._ensure_user_exists(user_id)

        if not text.strip():
            raise ValidationError("O texto do post nao pode estar vazio.")

        if not twitter_account_ids:
            raise ValidationError("Selecione ao menos uma conta do X.")

        for account_id in twitter_account_ids:
            account = self.twitter_account_repository.get(account_id)

            if account is None:
                raise NotFoundError("Conta do X nao encontrada.")

            if account.user_id != user_id:
                raise NotFoundError("Conta do X nao pertence ao usuario.")

        post = self.post_repository.create(
            {
                "user_id": user_id,
                "text": text.strip(),
                "status": PostStatus.PENDING,
            }
        )

        for account_id in twitter_account_ids:
            self.post_account_repository.create(
                {
                    "post_id": post.id,
                    "twitter_account_id": account_id,
                }
            )

        return post

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
        """
        post = self.post_repository.get(post_id)

        if post is None:
            raise NotFoundError("Post nao encontrado.")

        post_accounts = self.post_account_repository.list_by_post(post_id)

        # Idempotencia: contas ja publicadas com sucesso nunca sao
        # reprocessadas. Apenas PENDING/FAILED sao (re)tentadas.
        accounts_to_publish = [
            post_account
            for post_account in post_accounts
            if post_account.status != PostAccountStatus.PUBLISHED
        ]

        if accounts_to_publish:
            # Validacao completa de negocio ANTES de qualquer chamada
            # externa. Se a assinatura nao existir, estiver inativa ou
            # sem saldo suficiente para todas as contas pendentes,
            # nenhuma publicacao ocorre e a excecao sobe para a rota
            # (que faz rollback -- nada e alterado).
            subscription = self.subscription_service.ensure_can_publish(
                post.user_id,
                required_posts=len(accounts_to_publish),
            )

            for post_account in accounts_to_publish:
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

                    published_post = self.x_oauth_client.publish_post(
                        access_token=access_token,
                        text=post.text,
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
                    # `accounts_to_publish`); o consumo efetivo por
                    # conta publicada com sucesso mantem `used_posts`
                    # correto mesmo se parte das contas falhar.
                    self.subscription_service.consume_posts(
                        subscription.id,
                        1,
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
