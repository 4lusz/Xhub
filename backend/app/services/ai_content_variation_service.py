"""Service principal da Publicacao Inteligente.

Ver `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md` para a especificacao
oficial completa. Responsabilidades (conforme roadmap):

- Receber texto original e contas de destino.
- Determinar se a geracao e opcional, desnecessaria ou obrigatoria
  (1 conta / 2 a 4 contas / 5+ contas).
- Orquestrar cache.
- Chamar o cliente Groq quando necessario.
- Validar variacoes retornadas (preservacao exata de URLs, hashtags,
  @mencoes, emojis e CTA).
- Medir e registrar modelo, tempo, tokens, custo (quando aplicavel) e
  versao do prompt.
- Retornar preview seguro para a rota/frontend -- nunca publica no X.
- Tratar indisponibilidade da Groq de acordo com a regra oficial (nunca
  fazer fallback automatico para o mesmo texto em 5+ contas).
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic

from app.config.settings import settings
from app.core.exceptions import (
    BadRequestException,
    ServiceUnavailableException,
    UnauthorizedException,
)
from app.core.logging_config import get_logger
from app.domain.content_invariants import has_duplicates, is_duplicate_text, preserves_invariants
from app.domain.policies import OPTIONAL_VARIATION_MAX_ACCOUNTS
from app.integrations.groq_client import GroqClient
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.services.base_service import NotFoundError, ValidationError

logger = get_logger(__name__)

# Limite oficial do X/Twitter para um post de texto simples -- mesmo
# limite ja aplicado em `CreatePostRequest` (app.routes.post).
_MAX_POST_LENGTH = 280

STRATEGY_ORIGINAL = "original"
STRATEGY_OPTIONAL_VARIATION = "optional_variation"
STRATEGY_MANDATORY_VARIATION = "mandatory_variation"

_RECOMMENDATION_WARNING = (
    "Publicar o mesmo texto em varias contas aumenta o risco de bloqueios "
    "ou limitacoes automaticas pela plataforma X. Recomendamos manter a "
    "Publicacao Inteligente ativada para diversificar automaticamente "
    "suas publicacoes."
)

_INSUFFICIENT_VARIATIONS_MESSAGE = (
    "Nao foi possivel gerar variacoes validas e suficientes para todas as "
    "contas selecionadas. Voce pode tentar novamente, salvar o post como "
    "rascunho (sem publicar) ou reagendar a publicacao para mais tarde."
)


@dataclass(frozen=True)
class AccountPreview:
    twitter_account_id: uuid.UUID
    username: str
    display_name: str
    text: str
    is_variation: bool
    char_count: int


@dataclass(frozen=True)
class IntelligentPublicationPreview:
    original_text: str
    strategy: str
    is_variation_required: bool
    is_variation_applied: bool
    cache_hit: bool
    warning: str | None
    model: str | None
    prompt_version: str
    accounts: tuple[AccountPreview, ...]


class _InMemoryVariationCache:
    """Cache de variacoes em memoria, local a este processo.

    Mesma decisao arquitetural ja adotada em
    `app.middleware.rate_limit.RateLimitMiddleware`: estado em memoria
    de processo, sem dependencia de infraestrutura externa (Redis etc.)
    nao comprovadamente necessaria nesta etapa. Com multiplos
    workers/replicas, cada processo mantem seu proprio cache -- reduz a
    taxa de acerto, mas nunca compromete a corretude (nunca serve dado
    de um contexto diferente, pois a chave inclui texto original,
    contas, modelo e versao do prompt).

    Nao guarda nenhum segredo -- apenas os textos gerados, que sao
    tratados como dado do usuario (texto do proprio post).
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, tuple[str, ...]]] = {}

    def get(self, key: str) -> tuple[str, ...] | None:
        entry = self._store.get(key)
        if entry is None:
            return None

        expires_at, variations = entry
        if monotonic() >= expires_at:
            self._store.pop(key, None)
            return None

        return variations

    def set(self, key: str, variations: tuple[str, ...]) -> None:
        ttl_seconds = settings.INTELLIGENT_PUBLICATION_CACHE_TTL_SECONDS
        self._store[key] = (monotonic() + ttl_seconds, variations)


# Singleton em nivel de modulo -- precisa sobreviver entre requisicoes
# (diferente de `AIContentVariationService`, que e instanciado por
# requisicao via dependency injection, ver `app.auth.dependencies`).
_variation_cache = _InMemoryVariationCache()


def _build_cache_key(
    original_text: str, twitter_account_ids: Sequence[uuid.UUID]
) -> str:
    """Chave de cache: hash de texto original + contas selecionadas +
    modelo + versao do prompt -- invalida automaticamente quando
    qualquer um desses mudar (ver secao "Cache" do roadmap)."""
    normalized_ids = ",".join(sorted(str(account_id) for account_id in twitter_account_ids))
    raw_key = "|".join(
        [
            original_text,
            normalized_ids,
            settings.GROQ_MODEL,
            settings.AI_CONTENT_VARIATION_PROMPT_VERSION,
        ]
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _build_system_prompt(count: int) -> str:
    # Regra 4 e regra 8 foram reforcadas com base em auditoria empirica
    # (varias chamadas reais a Groq comparadas): a versao anterior do
    # prompt (a) deixava a IA ocasionalmente omitir a clausula de
    # urgencia/escassez do CTA (ex.: "e por tempo limitado") mesmo
    # mantendo o verbo de acao, e (b) produzia variacoes com vocabulario
    # diferente mas o MESMO esqueleto de frase (emoji sempre logo no
    # inicio, hashtags+mencao sempre agrupadas no fim) -- o que pode
    # continuar parecendo padronizado para deteccao de conteudo
    # repetitivo, mesmo sem repetir uma unica palavra. Testado antes e
    # depois com `preserves_invariants`/`has_duplicates`: a mudanca nao
    # afeta a preservacao de URLs/hashtags/@mencoes/emojis (continua
    # 100% garantida deterministicamente por
    # `app.domain.content_invariants`, independente do que o prompt
    # pedir) -- so melhora a qualidade estocastica da resposta da IA.
    return (
        "Voce reescreve posts para redes sociais gerando variacoes "
        "naturais que preservam EXATAMENTE o significado original. "
        "Regras obrigatorias e inegociaveis: "
        "1) mantenha todas as hashtags (#...) exatamente como estao; "
        "2) mantenha todas as @mencoes exatamente como estao; "
        "3) mantenha todos os emojis exatamente como estao; "
        "4) mantenha qualquer call-to-action (CTA) presente no texto "
        "original, incluindo qualquer senso de urgencia ou escassez "
        "associado a ele (ex.: tempo limitado, ultimas unidades, "
        "vagas restantes) -- nao omita essa clausula; "
        "5) NUNCA altere, expanda, resuma, reescreva ou modifique "
        "qualquer URL/link, incluindo encurtadores como bit.ly ou "
        "shopee -- copie cada URL exatamente, caractere por caractere; "
        "6) nunca invente informacao nova nem remova informacao "
        "existente; "
        "7) cada variacao deve ter no maximo "
        f"{_MAX_POST_LENGTH} caracteres; "
        "8) as variacoes devem ser diferentes entre si tanto no "
        "vocabulario quanto na estrutura da frase -- varie a ordem dos "
        "elementos (comece uma pelo CTA, outra pela descricao, outra "
        "por uma pergunta ou pela mencao), o tamanho das frases e a "
        "posicao de emojis/link/hashtags no texto, como pessoas "
        "diferentes escreveriam sobre o mesmo assunto; nunca repita o "
        "mesmo esqueleto de frase em duas variacoes; "
        "9) responda SOMENTE com um objeto JSON no formato exato "
        '{"variations": ["texto 1", "texto 2"]}, sem nenhum texto fora '
        "do JSON, contendo exatamente "
        f"{count} variacoes."
    )


def _build_user_prompt(original_text: str, count: int) -> str:
    return (
        f"Texto original:\n{original_text}\n\n"
        f"Gere exatamente {count} variacoes distintas deste texto, "
        "seguindo rigorosamente as regras definidas."
    )


class AIContentVariationService:
    """Orquestra a geracao de variacoes de texto para a Publicacao
    Inteligente. Nunca publica no X -- apenas retorna previews."""

    def __init__(
        self,
        groq_client: GroqClient,
        twitter_account_repository: TwitterAccountRepository,
    ) -> None:
        self.groq_client = groq_client
        self.twitter_account_repository = twitter_account_repository
        self._last_cache_hit = False
        self._last_model: str | None = None

    def generate_preview(
        self,
        *,
        user_id: uuid.UUID,
        original_text: str,
        twitter_account_ids: Sequence[uuid.UUID],
        apply_variation: bool = True,
    ) -> IntelligentPublicationPreview:
        """Ponto de entrada principal. Levanta excecao (nunca cria
        `Post`/`PostAccount` -- essa e responsabilidade exclusiva de
        `PostService`) quando a regra obrigatoria de 5+ contas nao pode
        ser cumprida."""
        if not original_text.strip():
            raise ValidationError("O texto original nao pode estar vazio.")

        if not twitter_account_ids:
            raise ValidationError("Selecione ao menos uma conta do X.")

        if len(original_text) > _MAX_POST_LENGTH:
            raise ValidationError(
                f"O texto original excede o limite de {_MAX_POST_LENGTH} "
                "caracteres."
            )

        accounts = self._load_and_validate_accounts(user_id, twitter_account_ids)
        count = len(accounts)

        logger.info(
            "Iniciando geracao de preview da Publicacao Inteligente.",
            extra={"account_count": count},
        )

        if count == 1:
            # 1 conta: nunca chama a Groq por obrigatoriedade.
            preview_result = self._build_original_preview(
                original_text,
                accounts,
                strategy=STRATEGY_ORIGINAL,
                required=False,
                applied=False,
                warning=None,
            )
        elif count <= OPTIONAL_VARIATION_MAX_ACCOUNTS:
            preview_result = self._generate_optional_preview(
                original_text, accounts, apply_variation=apply_variation
            )
        else:
            preview_result = self._generate_mandatory_preview(original_text, accounts)

        logger.info(
            "Preview da Publicacao Inteligente concluido.",
            extra={
                "account_count": count,
                "strategy": preview_result.strategy,
                "is_variation_required": preview_result.is_variation_required,
                "is_variation_applied": preview_result.is_variation_applied,
                "cache_hit": preview_result.cache_hit,
            },
        )

        return preview_result

    # ------------------------------------------------------------------ #
    # Estrategias por quantidade de contas
    # ------------------------------------------------------------------ #

    def _generate_optional_preview(
        self, original_text: str, accounts: list, *, apply_variation: bool
    ) -> IntelligentPublicationPreview:
        """2 a 4 contas: publicar texto original e a regra oficial: a
        variacao e opcional (ativada por padrao no frontend). Qualquer
        falha da Groq aqui cai para o texto original -- nunca bloqueia
        a publicacao (roadmap: "publicar texto original e permitido
        pela regra oficial se a variacao opcional nao puder ser gerada
        ou nao for confirmada")."""
        if not apply_variation:
            return self._build_original_preview(
                original_text,
                accounts,
                strategy=STRATEGY_OPTIONAL_VARIATION,
                required=False,
                applied=False,
                warning=_RECOMMENDATION_WARNING,
            )

        try:
            variations = self._get_or_generate_variations(
                original_text,
                [account.id for account in accounts],
                len(accounts),
            )
        except (ServiceUnavailableException, UnauthorizedException, BadRequestException, ValidationError) as exc:
            logger.warning(
                "Variacao opcional (2-4 contas) indisponivel -- "
                "publicando texto original conforme regra oficial.",
                extra={"account_count": len(accounts), "error": str(exc)},
            )
            return self._build_original_preview(
                original_text,
                accounts,
                strategy=STRATEGY_OPTIONAL_VARIATION,
                required=False,
                applied=False,
                warning=_RECOMMENDATION_WARNING,
            )

        return self._build_variation_preview(
            original_text,
            accounts,
            variations,
            strategy=STRATEGY_OPTIONAL_VARIATION,
            required=False,
        )

    def _generate_mandatory_preview(
        self, original_text: str, accounts: list
    ) -> IntelligentPublicationPreview:
        """5+ contas: geracao obrigatoria. Nunca ha fallback automatico
        para o texto original -- se a Groq estiver indisponivel e nao
        houver cache valido, a excecao propaga para a rota, que
        interrompe o fluxo ANTES de qualquer criacao de `Post` (ver
        `app.routes.intelligent_publication`)."""
        try:
            variations = self._get_or_generate_variations(
                original_text,
                [account.id for account in accounts],
                len(accounts),
            )
        except (ServiceUnavailableException, UnauthorizedException, BadRequestException, ValidationError):
            logger.error(
                "Publicacao interrompida: geracao obrigatoria de "
                "variacoes (5+ contas) nao pode ser concluida.",
                extra={"account_count": len(accounts)},
            )
            raise

        return self._build_variation_preview(
            original_text,
            accounts,
            variations,
            strategy=STRATEGY_MANDATORY_VARIATION,
            required=True,
        )

    # ------------------------------------------------------------------ #
    # Geracao + cache + validacao
    # ------------------------------------------------------------------ #

    def _get_or_generate_variations(
        self,
        original_text: str,
        twitter_account_ids: Sequence[uuid.UUID],
        count: int,
    ) -> tuple[str, ...]:
        cache_key = _build_cache_key(original_text, twitter_account_ids)

        if settings.INTELLIGENT_PUBLICATION_CACHE_ENABLED:
            cached = _variation_cache.get(cache_key)
            if cached is not None and len(cached) >= count:
                logger.info(
                    "Cache hit para variacoes da Publicacao Inteligente.",
                    extra={"account_count": count},
                )
                self._last_cache_hit = True
                return cached[:count]

        self._last_cache_hit = False

        valid_variations = self._request_valid_variations(original_text, count)

        if len(valid_variations) < count:
            missing = count - len(valid_variations)
            logger.info(
                "Variacoes insuficientes na primeira tentativa -- "
                "complementando.",
                extra={"missing": missing},
            )
            extra_variations = self._request_valid_variations(
                original_text, missing, exclude=valid_variations
            )
            valid_variations = valid_variations + tuple(
                candidate
                for candidate in extra_variations
                if not any(
                    is_duplicate_text(candidate, existing)
                    for existing in valid_variations
                )
            )

        if len(valid_variations) < count or has_duplicates(list(valid_variations[:count])):
            logger.warning(
                "Nao foi possivel obter variacoes validas e suficientes.",
                extra={"required": count, "obtained": len(valid_variations)},
            )
            raise ValidationError(_INSUFFICIENT_VARIATIONS_MESSAGE)

        result = valid_variations[:count]

        if settings.INTELLIGENT_PUBLICATION_CACHE_ENABLED:
            _variation_cache.set(cache_key, result)

        return result

    def _request_valid_variations(
        self,
        original_text: str,
        count: int,
        *,
        exclude: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        system_prompt = _build_system_prompt(count)
        user_prompt = _build_user_prompt(original_text, count)

        result = self.groq_client.generate_variations(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            count=count,
        )
        self._last_model = result.model

        logger.info(
            "Resposta da Groq recebida para geracao de variacoes.",
            extra={
                "model": result.model,
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "prompt_version": settings.AI_CONTENT_VARIATION_PROMPT_VERSION,
            },
        )

        valid: list[str] = []
        for candidate in result.variations:
            if len(candidate) > _MAX_POST_LENGTH:
                continue

            # Reforco deterministico das regras do prompt (roadmap:
            # "Mesmo que a Groq retorne uma variacao que altere URL,
            # parametros, dominio, encurtador, hashtag, @mencao, emoji
            # ou CTA, a resposta deve ser considerada invalida").
            if not preserves_invariants(original_text, candidate):
                logger.warning(
                    "Variacao descartada: nao preserva elementos "
                    "imutaveis do texto original."
                )
                continue

            if is_duplicate_text(candidate, original_text):
                continue

            if any(is_duplicate_text(candidate, existing) for existing in valid):
                continue

            if any(is_duplicate_text(candidate, existing) for existing in exclude):
                continue

            valid.append(candidate)

        return tuple(valid)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _load_and_validate_accounts(
        self, user_id: uuid.UUID, twitter_account_ids: Sequence[uuid.UUID]
    ) -> list:
        accounts = []
        seen: set[uuid.UUID] = set()

        for account_id in twitter_account_ids:
            if account_id in seen:
                raise ValidationError(
                    "twitter_account_ids nao pode conter ids duplicados."
                )
            seen.add(account_id)

            account = self.twitter_account_repository.get(account_id)
            if account is None:
                raise NotFoundError("Conta do X nao encontrada.")

            if account.user_id != user_id:
                raise NotFoundError("Conta do X nao pertence ao usuario.")

            accounts.append(account)

        return accounts

    def _build_original_preview(
        self,
        original_text: str,
        accounts: list,
        *,
        strategy: str,
        required: bool,
        applied: bool,
        warning: str | None,
    ) -> IntelligentPublicationPreview:
        return IntelligentPublicationPreview(
            original_text=original_text,
            strategy=strategy,
            is_variation_required=required,
            is_variation_applied=applied,
            cache_hit=False,
            warning=warning,
            model=None,
            prompt_version=settings.AI_CONTENT_VARIATION_PROMPT_VERSION,
            accounts=tuple(
                AccountPreview(
                    twitter_account_id=account.id,
                    username=account.username,
                    display_name=account.display_name,
                    text=original_text,
                    is_variation=False,
                    char_count=len(original_text),
                )
                for account in accounts
            ),
        )

    def _build_variation_preview(
        self,
        original_text: str,
        accounts: list,
        variations: tuple[str, ...],
        *,
        strategy: str,
        required: bool,
    ) -> IntelligentPublicationPreview:
        warning = _RECOMMENDATION_WARNING if strategy == STRATEGY_OPTIONAL_VARIATION else None

        return IntelligentPublicationPreview(
            original_text=original_text,
            strategy=strategy,
            is_variation_required=required,
            is_variation_applied=True,
            cache_hit=self._last_cache_hit,
            warning=warning,
            model=self._last_model,
            prompt_version=settings.AI_CONTENT_VARIATION_PROMPT_VERSION,
            accounts=tuple(
                AccountPreview(
                    twitter_account_id=account.id,
                    username=account.username,
                    display_name=account.display_name,
                    text=variation,
                    is_variation=True,
                    char_count=len(variation),
                )
                for account, variation in zip(accounts, variations)
            ),
        )
