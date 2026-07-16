"""Cliente HTTP para OAuth 2.0, User Lookup e upload de midia da API oficial do X."""

import base64
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
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
# Base do endpoint v2 nativo de upload de midia. Diferente do endpoint
# legado v1.1 (`upload.twitter.com/1.1/media/upload.json`, um unico
# endpoint com um campo `command=INIT|APPEND|FINALIZE|STATUS`), o
# endpoint v2 usa um CAMINHO dedicado por etapa:
#   POST /2/media/upload/initialize        (JSON body)
#   POST /2/media/upload/{id}/append       (multipart/form-data)
#   POST /2/media/upload/{id}/finalize     (sem corpo)
#   GET  /2/media/upload/{id}/status
# Confirmado empiricamente (chamada real contra a API do X, 2026-07):
# a primeira versao desta implementacao usava o padrao antigo
# (`command=INIT` em multipart no endpoint base) e recebia
# 400 "Missing media field in JSON" -- o X so aceita o formato acima.
# Aceita Bearer OAuth2 de contexto de usuario (mesmo token usado em
# todo o resto deste cliente), desde que o escopo `media.write` tenha
# sido concedido -- ver `settings.X_OAUTH_SCOPES`.
X_MEDIA_UPLOAD_URL = "https://api.x.com/2/media/upload"

# Estados terminais/nao-terminais do processamento assincrono de
# midia (gif/video) reportado pelo comando STATUS -- ver
# `XOAuthClient._wait_for_media_processing`.
_MEDIA_PROCESSING_SUCCEEDED = "succeeded"
_MEDIA_PROCESSING_FAILED = "failed"


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
    profile_image_url: str | None = None


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
        # `user.fields=profile_image_url` (ver docs/ROADMAP_MEDIA.md,
        # secao "Contas conectadas"): sem este parametro a API v2 do X
        # nao inclui a foto de perfil na resposta por padrao.
        params = {"user.fields": "profile_image_url"}

        with httpx.Client(timeout=10.0) as client:
            response = client.get(X_ME_URL, headers=headers, params=params)

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
        media_ids: list[str] | None = None,
    ) -> XPublishedPost:
        if not access_token:
            raise UnauthorizedException("Access token invalido.")

        if not text.strip():
            raise BadRequestException("Texto do post vazio.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "text": text.strip(),
        }
        # Midia (ver docs/ROADMAP_MEDIA.md): `media_ids` sao ids
        # retornados pelo proprio X ao final de `upload_media` abaixo
        # (upload feito nesta mesma conta, ANTES desta chamada -- ver
        # `PostService.publish_post`). Identica para todas as contas do
        # post; nunca gerada/alterada pela Publicacao Inteligente.
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

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

    def upload_media(
        self,
        *,
        access_token: str,
        file_path: Path | str,
        content_type: str,
        media_category: str,
        total_bytes: int,
    ) -> str:
        """Envia um arquivo de midia (imagem/gif/video) para o X usando
        os endpoints v2 dedicados de upload (initialize/append/finalize/
        status, cada um sob `/2/media/upload/{id}/...`). Retorna o
        `media_id` do X, pronto para ser usado em
        `publish_post(media_ids=[...])`.

        Midia e enviada UMA VEZ POR CONTA de destino: cada conta do X
        tem seu proprio `access_token` e sua propria biblioteca de
        midia, entao o mesmo arquivo local precisa ser enviado
        novamente para cada conta antes de publicar (ver
        `PostService.publish_post`) -- o arquivo em si (bytes) e
        sempre identico, apenas o destino (conta) muda.
        """
        if not access_token:
            raise UnauthorizedException("Access token invalido.")

        media_id = self._media_initialize(
            access_token=access_token,
            total_bytes=total_bytes,
            content_type=content_type,
            media_category=media_category,
        )
        self._media_append(
            access_token=access_token,
            media_id=media_id,
            file_path=Path(file_path),
        )
        processing_info = self._media_finalize(access_token=access_token, media_id=media_id)

        if processing_info is not None:
            self._wait_for_media_processing(
                access_token=access_token,
                media_id=media_id,
                processing_info=processing_info,
            )

        return media_id

    def _media_initialize(
        self,
        *,
        access_token: str,
        total_bytes: int,
        content_type: str,
        media_category: str,
    ) -> str:
        # `POST /2/media/upload/initialize`, corpo JSON -- confirmado
        # empiricamente (chamada real contra a API do X, 2026-07)
        # apos o padrao antigo (`POST /2/media/upload` com
        # `command=INIT` em multipart, herdado do endpoint legado
        # v1.1) retornar 400 "Missing media field in JSON": o endpoint
        # v2 na verdade usa caminhos dedicados por etapa, nao um unico
        # endpoint com campo `command`.
        response = self._media_request(
            method="POST",
            path="initialize",
            access_token=access_token,
            json_body={
                "media_type": content_type,
                "total_bytes": total_bytes,
                "media_category": media_category,
            },
            context="Upload de midia (INIT)",
        )
        payload = response.json()
        media_id = (payload.get("data") or {}).get("id")

        if not media_id:
            raise BadRequestException("Resposta do X (INIT de upload de midia) sem media_id.")

        return str(media_id)

    def _media_append(self, *, access_token: str, media_id: str, file_path: Path) -> None:
        chunk_size = settings.X_MEDIA_UPLOAD_CHUNK_SIZE_BYTES
        segment_index = 0

        with file_path.open("rb") as source:
            while True:
                chunk = source.read(chunk_size)
                if not chunk:
                    break

                # `POST /2/media/upload/{id}/append`, multipart/form-data
                # com o chunk binario (`media`) e o indice do segmento.
                self._media_request(
                    method="POST",
                    path=f"{media_id}/append",
                    access_token=access_token,
                    multipart_fields={"segment_index": (None, str(segment_index))},
                    files={"media": ("chunk", chunk, "application/octet-stream")},
                    context="Upload de midia (APPEND)",
                )
                segment_index += 1

    def _media_finalize(self, *, access_token: str, media_id: str) -> dict[str, Any] | None:
        # `POST /2/media/upload/{id}/finalize`, sem corpo.
        response = self._media_request(
            method="POST",
            path=f"{media_id}/finalize",
            access_token=access_token,
            context="Upload de midia (FINALIZE)",
        )
        payload = response.json()
        processing_info = (payload.get("data") or {}).get("processing_info")
        return processing_info if isinstance(processing_info, dict) else None

    def _wait_for_media_processing(
        self,
        *,
        access_token: str,
        media_id: str,
        processing_info: dict[str, Any],
    ) -> None:
        """Espera ativamente (poll) o X terminar de transcodificar/validar
        um gif/video ja enviado (FINALIZE assincrono), respeitando o
        `check_after_secs` sugerido pelo proprio X a cada consulta, ate
        `settings.X_MEDIA_STATUS_MAX_WAIT_SECONDS` no total.

        NOTA: o caminho `GET /2/media/upload/{id}/status` usado aqui
        segue o mesmo padrao REST confirmado empiricamente para
        initialize/append/finalize, mas NAO foi testado contra a API
        real (so aciona para gif/video, que exigem processamento
        assincrono -- imagem nunca chega a chamar este metodo, pois
        `_media_finalize` nao retorna `processing_info` para imagem).
        Validar contra uma conta real na primeira publicacao com
        gif/video.
        """
        deadline = time.monotonic() + settings.X_MEDIA_STATUS_MAX_WAIT_SECONDS
        info = processing_info

        while True:
            state = info.get("state")

            if state == _MEDIA_PROCESSING_SUCCEEDED:
                return

            if state == _MEDIA_PROCESSING_FAILED:
                error = info.get("error") if isinstance(info.get("error"), dict) else {}
                raise BadRequestException(
                    "Processamento de midia falhou no X: "
                    f"{error.get('message') or state or 'motivo desconhecido'}"
                )

            check_after_secs = info.get("check_after_secs") or 1
            if time.monotonic() + check_after_secs > deadline:
                raise ServiceUnavailableException(
                    "Timeout aguardando o processamento da midia (gif/video) pelo X."
                )

            time.sleep(check_after_secs)

            response = self._media_request(
                method="GET",
                path=f"{media_id}/status",
                access_token=access_token,
                context="Upload de midia (STATUS)",
            )
            payload = response.json()
            next_info = (payload.get("data") or {}).get("processing_info")
            info = next_info if isinstance(next_info, dict) else {"state": _MEDIA_PROCESSING_SUCCEEDED}

    def _media_request(
        self,
        *,
        method: str,
        path: str,
        access_token: str,
        json_body: dict[str, Any] | None = None,
        multipart_fields: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        context: str,
    ) -> httpx.Response:
        """Chamada HTTP generica para os endpoints v2 dedicados de
        upload de midia (`/2/media/upload/...`) -- cada etapa
        (initialize/append/finalize/status) usa um metodo/caminho e
        formato de corpo diferentes, unificados aqui apenas para
        tratamento de erro/timeout comum."""
        url = f"{X_MEDIA_UPLOAD_URL}/{path}" if path else X_MEDIA_UPLOAD_URL
        headers = {"Authorization": f"Bearer {access_token}"}

        request_kwargs: dict[str, Any] = {}
        if json_body is not None:
            request_kwargs["json"] = json_body
        elif multipart_fields is not None or files is not None:
            merged_files: dict[str, Any] = dict(multipart_fields or {})
            merged_files.update(files or {})
            request_kwargs["files"] = merged_files

        try:
            with httpx.Client(timeout=settings.X_MEDIA_UPLOAD_TIMEOUT_SECONDS) as client:
                response = client.request(method, url, headers=headers, **request_kwargs)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableException(f"Timeout ao enviar midia para o X ({context}).") from exc
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"Erro de conexao ao enviar midia para o X ({context}): {exc}"
            ) from exc

        self._raise_for_media_error(response, context=context)
        return response

    def _raise_for_media_error(self, response: httpx.Response, *, context: str) -> None:
        """Mesma preservacao de motivo original (`_extract_error_detail`)
        e mapeamento de status HTTP ja usados em `publish_post`,
        reaproveitados aqui para o endpoint de upload de midia."""
        if response.status_code == 401:
            raise UnauthorizedException(
                f"{context}: 401 Unauthorized da API do X: {self._extract_error_detail(response)}"
            )

        if response.status_code == 403:
            raise ForbiddenException(
                f"{context}: 403 Forbidden da API do X: {self._extract_error_detail(response)}"
            )

        if response.status_code == 429:
            raise ServiceUnavailableException(
                f"{context}: 429 Too Many Requests da API do X: {self._extract_error_detail(response)}"
            )

        if response.status_code >= 500:
            raise ServiceUnavailableException(
                f"{context}: {response.status_code} - API do X indisponivel: "
                f"{self._extract_error_detail(response)}"
            )

        if response.status_code >= 400:
            raise BadRequestException(
                f"{context}: {response.status_code} - {self._extract_error_detail(response)}"
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
        raw_profile_image_url = data.get("profile_image_url")

        if not isinstance(twitter_user_id, str) or not twitter_user_id:
            raise BadRequestException("Resposta do X sem id do usuario.")
        if not isinstance(username, str) or not username:
            raise BadRequestException("Resposta do X sem username.")
        if not isinstance(display_name, str) or not display_name:
            raise BadRequestException("Resposta do X sem nome do usuario.")

        profile_image_url = None
        if isinstance(raw_profile_image_url, str) and raw_profile_image_url:
            profile_image_url = self._upgrade_profile_image_resolution(raw_profile_image_url)

        return XUserProfile(
            twitter_user_id=twitter_user_id,
            username=username,
            display_name=display_name,
            profile_image_url=profile_image_url,
        )

    def _upgrade_profile_image_resolution(self, profile_image_url: str) -> str:
        """O X retorna por padrao a miniatura `_normal` (48x48). Trocar
        pelo sufixo `_400x400` (suportado pelo mesmo CDN, mesma URL
        base) da uma foto de perfil nitida na UI sem exigir nenhuma
        chamada extra a API -- pura manipulacao de string, com fallback
        seguro (URL original) se o padrao esperado nao for encontrado."""
        if "_normal." in profile_image_url:
            return profile_image_url.replace("_normal.", "_400x400.")
        return profile_image_url
