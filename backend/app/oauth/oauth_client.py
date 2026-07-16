"""Cliente HTTP para OAuth 2.0 e User Lookup da API oficial do X."""

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from app.config.settings import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    ServiceUnavailableException,
    UnauthorizedException,
)

_ERROR_DETAIL_MAX_LENGTH = 500

X_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_ME_URL = "https://api.x.com/2/users/me"
X_POST_URL = "https://api.x.com/2/tweets"


@dataclass(frozen=True)
class XOAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime


@dataclass(frozen=True)
class XUserProfile:
    twitter_user_id: str
    username: str
    display_name: str


@dataclass(frozen=True)
class XPublishedPost:
    post_id: str


class XOAuthClient:
    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        self._ensure_oauth_settings()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.X_CLIENT_ID,
                "redirect_uri": settings.X_CALLBACK_URL,
                "scope": settings.X_OAUTH_SCOPES,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            quote_via=quote,
        )
        return f"{X_AUTHORIZE_URL}?{query}"

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extrai a mensagem de erro original da resposta da API do X,
        preservando o maximo de detalhe possivel para fins de auditoria
        (ver `PostAccount.error_message`). A API v2 do X segue o formato
        RFC 7807 (`title`/`detail`/`type`) na maioria dos erros -- ex.:
        `{"title": "UsageCapExceeded", "detail": "Usage cap exceeded: ..."}`
        -- mas nunca lanca excecao por conta de um corpo inesperado:
        sempre retorna algo utilizavel, mesmo que nao seja JSON.
        """
        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            return text[:_ERROR_DETAIL_MAX_LENGTH] if text else "sem corpo de resposta"

        if isinstance(payload, dict):
            title = payload.get("title")
            detail = payload.get("detail")
            if title and detail and str(title) != str(detail):
                return f"{title}: {detail}"[:_ERROR_DETAIL_MAX_LENGTH]
            if detail:
                return str(detail)[:_ERROR_DETAIL_MAX_LENGTH]
            if title:
                return str(title)[:_ERROR_DETAIL_MAX_LENGTH]

            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                messages = [
                    str(item.get("message"))
                    for item in errors
                    if isinstance(item, dict) and item.get("message")
                ]
                if messages:
                    return "; ".join(messages)[:_ERROR_DETAIL_MAX_LENGTH]

        text = response.text.strip()
        return text[:_ERROR_DETAIL_MAX_LENGTH] if text else "sem corpo de resposta"

    def exchange_code_for_tokens(self, *, code: str, code_verifier: str) -> XOAuthTokens:
        self._ensure_oauth_settings()
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.X_CALLBACK_URL,
            "code_verifier": code_verifier,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if settings.X_CLIENT_SECRET:
            headers["Authorization"] = self._basic_auth_header()
        else:
            data["client_id"] = settings.X_CLIENT_ID

        with httpx.Client(timeout=10.0) as client:
            response = client.post(X_TOKEN_URL, data=data, headers=headers)

        if response.status_code >= 400:
            raise UnauthorizedException("Falha ao trocar authorization code por tokens.")

        payload = response.json()
        return self._parse_tokens(payload)

    def refresh_access_token(self, *, refresh_token: str) -> XOAuthTokens:
        self._ensure_oauth_settings()
        if not refresh_token:
            raise UnauthorizedException("Refresh token invalido.")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if settings.X_CLIENT_SECRET:
            headers["Authorization"] = self._basic_auth_header()
        else:
            data["client_id"] = settings.X_CLIENT_ID

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(X_TOKEN_URL, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableException(
                "Timeout ao renovar token de acesso do X."
            ) from exc
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"Erro de conexao ao renovar token de acesso do X: {exc}"
            ) from exc

        if response.status_code >= 400:
            # Access Token expirado e o refresh tambem falhou -- preserva
            # o motivo original do X (ver `_extract_error_detail`) em vez
            # de uma mensagem generica, para auditoria/suporte.
            raise UnauthorizedException(
                f"Falha ao renovar token de acesso do X (Access Token "
                f"expirado): {response.status_code} - "
                f"{self._extract_error_detail(response)}"
            )

        return self._parse_tokens(response.json())
    def get_authenticated_user(self, access_token: str) -> XUserProfile:
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(timeout=10.0) as client:
            response = client.get(X_ME_URL, headers=headers)

        if response.status_code >= 400:
            raise UnauthorizedException("Falha ao buscar usuario autenticado no X.")

        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BadRequestException("Resposta invalida da API do X.")

        return self._parse_user(data)
    
    def publish_post(
        self,
        *,
        access_token: str,
        text: str,
    ) -> XPublishedPost:
        if not access_token:
            raise UnauthorizedException("Access token invalido.")

        if not text.strip():
            raise BadRequestException("Texto do post vazio.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "text": text.strip(),
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    X_POST_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableException(
                "Timeout ao conectar com a API do X."
            ) from exc
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"Erro de conexao com a API do X: {exc}"
            ) from exc

        # Cada branch abaixo preserva o motivo original retornado pelo X
        # (`_extract_error_detail`) junto do status HTTP, para que o
        # motivo exato da falha (ex.: "UsageCapExceeded: Usage cap
        # exceeded: Monthly product cap") fique disponivel para auditoria
        # -- ver `PostAccount.error_message` e `PostService.publish_post`,
        # que gravam `exc.message` sem nenhuma alteracao na logica de
        # publicacao em si (mesmos tipos de excecao, mesmos branches).
        if response.status_code == 401:
            raise UnauthorizedException(
                f"401 Unauthorized da API do X: "
                f"{self._extract_error_detail(response)}"
            )

        if response.status_code == 403:
            raise ForbiddenException(
                f"403 Forbidden da API do X: "
                f"{self._extract_error_detail(response)}"
            )

        if response.status_code == 429:
            raise ServiceUnavailableException(
                f"429 Too Many Requests da API do X: "
                f"{self._extract_error_detail(response)}"
            )

        if response.status_code >= 500:
            raise ServiceUnavailableException(
                f"{response.status_code} - API do X indisponivel: "
                f"{self._extract_error_detail(response)}"
            )

        if response.status_code >= 400:
            raise BadRequestException(
                f"{response.status_code} - Falha ao publicar no X: "
                f"{self._extract_error_detail(response)}"
            )

        payload = response.json()
        data = payload.get("data")

        if not isinstance(data, dict):
            raise BadRequestException("Resposta invalida da API do X.")

        post_id = data.get("id")

        if not isinstance(post_id, str) or not post_id:
            raise BadRequestException("Resposta da API do X sem id do post.")

        return XPublishedPost(
            post_id=post_id,
        )

    def _basic_auth_header(self) -> str:
        credentials = f"{settings.X_CLIENT_ID}:{settings.X_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    def _ensure_oauth_settings(self) -> None:
        if not settings.X_CLIENT_ID:
            raise BadRequestException("X_CLIENT_ID nao configurado.")
        if not settings.X_CALLBACK_URL:
            raise BadRequestException("X_CALLBACK_URL nao configurado.")

    def _parse_tokens(self, payload: dict[str, Any]) -> XOAuthTokens:
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        expires_in = payload.get("expires_in", 7200)

        if not isinstance(access_token, str) or not access_token:
            raise BadRequestException("Resposta de token sem access_token.")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise BadRequestException("Resposta de token sem refresh_token.")
        if not isinstance(expires_in, int):
            raise BadRequestException("Resposta de token com expires_in invalido.")

        return XOAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    def _parse_user(self, data: dict[str, Any]) -> XUserProfile:
        twitter_user_id = data.get("id")
        username = data.get("username")
        display_name = data.get("name")

        if not isinstance(twitter_user_id, str) or not twitter_user_id:
            raise BadRequestException("Resposta do X sem id do usuario.")
        if not isinstance(username, str) or not username:
            raise BadRequestException("Resposta do X sem username.")
        if not isinstance(display_name, str) or not display_name:
            raise BadRequestException("Resposta do X sem nome do usuario.")

        return XUserProfile(
            twitter_user_id=twitter_user_id,
            username=username,
            display_name=display_name,
        )
