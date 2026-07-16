"""Cliente HTTP da Groq -- integracao isolada da Publicacao Inteligente.

Segue o mesmo padrao de `app.oauth.oauth_client.XOAuthClient`: cliente
HTTP dedicado, sem conhecer models SQLAlchemy nem regras de negocio.
Toda decisao de negocio (quando chamar, como tratar indisponibilidade,
validacao semantica das variacoes) fica em
`app.services.ai_content_variation_service.AIContentVariationService`.

Usa o endpoint de chat completions da Groq, compativel com o formato da
OpenAI (`/openai/v1/chat/completions`), mas SEM usar a OpenAI --
requisito explicito do roadmap oficial (ver
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

from app.config.settings import settings
from app.core.exceptions import (
    BadRequestException,
    ServiceUnavailableException,
    UnauthorizedException,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


@dataclass(frozen=True)
class GroqVariationResult:
    """Resultado de uma chamada de geracao de variacoes.

    Carrega os metadados exigidos pelo roadmap para logging/observabilidade
    (modelo, tempo, tokens, custo) -- nunca o texto do prompt completo.
    """

    variations: tuple[str, ...]
    model: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class GroqClient:
    """Cliente dedicado para a API da Groq. Nunca loga a API key nem o
    prompt/resposta completos -- ver `app.core.logging_config`."""

    def generate_variations(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        count: int,
    ) -> GroqVariationResult:
        """Solicita `count` variacoes de texto em uma unica chamada
        (reduz custo/latencia comparado a `count` chamadas separadas).

        A resposta esperada do modelo e um objeto JSON estrito
        `{"variations": ["...", ...]}` com exatamente `count` itens --
        reforcado via `response_format: json_object` e validado
        estruturalmente aqui. A validacao SEMANTICA (preservacao de
        URLs/hashtags/@mencoes/emojis, duplicatas) e responsabilidade do
        `AIContentVariationService`, nao deste cliente.
        """
        self._ensure_configured()

        payload = {
            "model": settings.GROQ_MODEL,
            "temperature": 0.9,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        started_at = time.monotonic()
        try:
            with httpx.Client(timeout=settings.GROQ_TIMEOUT_SECONDS) as client:
                response = client.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            logger.warning(
                "Timeout ao chamar a Groq.",
                extra={"timeout_seconds": settings.GROQ_TIMEOUT_SECONDS},
            )
            raise ServiceUnavailableException(
                "A Groq nao respondeu a tempo."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Erro de rede ao chamar a Groq.", extra={"error": str(exc)})
            raise ServiceUnavailableException(
                "Falha de rede ao contatar a Groq."
            ) from exc

        latency_ms = int((time.monotonic() - started_at) * 1000)

        # Erros 401/403 indicam configuracao invalida (auditoria/roadmap:
        # nunca logar a API key).
        if response.status_code in (401, 403):
            logger.error(
                "Groq recusou a requisicao por credenciais invalidas.",
                extra={"status_code": response.status_code},
            )
            raise UnauthorizedException(
                "Configuracao da Groq invalida (GROQ_API_KEY)."
            )

        # 429: limite temporario -- tratado como indisponibilidade, nao
        # como erro do cliente, para que o service saiba que pode tentar
        # novamente mais tarde.
        if response.status_code == 429:
            logger.warning("Groq retornou 429 (rate limit).")
            raise ServiceUnavailableException(
                "Limite de requisicoes da Groq atingido temporariamente."
            )

        if response.status_code >= 500:
            logger.warning(
                "Groq indisponivel.", extra={"status_code": response.status_code}
            )
            raise ServiceUnavailableException("A Groq esta indisponivel no momento.")

        if response.status_code >= 400:
            logger.warning(
                "Groq retornou erro de requisicao.",
                extra={"status_code": response.status_code},
            )
            raise BadRequestException("Falha ao gerar variacoes com a Groq.")

        return self._parse_response(response, latency_ms=latency_ms, count=count)

    def _parse_response(
        self, response: httpx.Response, *, latency_ms: int, count: int
    ) -> GroqVariationResult:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise BadRequestException("Resposta invalida da Groq (JSON malformado).") from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise BadRequestException("Resposta da Groq sem choices.")

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None

        if not isinstance(content, str) or not content.strip():
            raise BadRequestException("Resposta da Groq sem conteudo.")

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise BadRequestException(
                "Resposta da Groq nao e um JSON valido de variacoes."
            ) from exc

        variations = (
            parsed_content.get("variations")
            if isinstance(parsed_content, dict)
            else None
        )

        if not isinstance(variations, list) or not all(
            isinstance(item, str) and item.strip() for item in variations
        ):
            raise BadRequestException(
                "Resposta da Groq nao contem uma lista valida de variacoes."
            )

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}

        result = GroqVariationResult(
            variations=tuple(item.strip() for item in variations),
            model=str(payload.get("model") or settings.GROQ_MODEL),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

        logger.info(
            "Variacoes geradas pela Groq.",
            extra={
                "model": result.model,
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "variations_count": len(result.variations),
                "requested_count": count,
            },
        )

        return result

    def _ensure_configured(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ServiceUnavailableException(
                "GROQ_API_KEY nao configurada."
            )

    def validate_configuration(self) -> None:
        """Valida a configuracao da Groq no startup sem fazer chamadas.

        A aplicacao deve detectar o problema de deploy/segredo ausente
        antes de aceitar requisicoes que dependem da Publicacao
        Inteligente.
        """
        self._ensure_configured()
