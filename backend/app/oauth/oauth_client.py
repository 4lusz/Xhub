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
    UnauthorizedException,
)

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

        with httpx.Client(timeout=10.0) as client:
            response = client.post(X_TOKEN_URL, data=data, headers=headers)

        if response.status_code >= 400:
            raise UnauthorizedException("Falha ao renovar token de acesso do X.")

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

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                X_POST_URL,
                headers=headers,
                json=payload,
            )

        if response.status_code == 401:
            raise UnauthorizedException(
                "Token de acesso invalido ou expirado."
            )

        if response.status_code == 403:
            raise ForbiddenException(
                "A conta nao possui permissao para publicar."
            )

        if response.status_code == 429:
            raise BadRequestException(
                "Limite de requisicoes da API do X atingido."
            )

        if response.status_code >= 500:
            raise BadRequestException(
                "A API do X esta indisponivel no momento."
           )

        if response.status_code >= 400:
            raise BadRequestException(
                "Falha ao publicar post no X."
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
