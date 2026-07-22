"""Rotas para conectar contas do X via OAuth 2.0 com PKCE."""

from html import escape
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_x_oauth_service
from app.config.settings import settings
from app.core.exceptions import BaseAppException, UnauthorizedException
from app.database.session import get_db
from app.models.user import User
from app.oauth.oauth_service import XOAuthService


class OAuthLoginResponse(BaseModel):
    authorization_url: str


router = APIRouter(prefix="/oauth/x", tags=["oauth"])


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED

    raise HTTPException(status_code=status_code, detail=exc.message) from exc


def _safe_redirect_message(message: str) -> str:
    return escape(message, quote=True)[:160]


def _frontend_redirect(**params: str) -> RedirectResponse:
    """Correcao (adicao do site publico de marketing em `FRONTEND_URL`
    -- a raiz): antes redirecionava para a raiz do frontend, que era a
    propria tela autenticada de contas conectadas. Com a raiz virando a
    landing page publica, redirecionar para la faria o toast de
    sucesso/erro do OAuth (`useOAuthCallbackFeedback`, montado apenas no
    layout autenticado) nunca ser exibido. Redireciona para
    `/accounts` -- tela autenticada onde a conexao foi iniciada -- que
    continua dentro do layout que captura esses parametros de query."""
    if "message" in params:
        params["message"] = _safe_redirect_message(params["message"])
    query = urlencode(params)
    frontend_accounts_url = f"{settings.FRONTEND_URL}/accounts"
    separator = "&" if "?" in frontend_accounts_url else "?"
    return RedirectResponse(f"{frontend_accounts_url}{separator}{query}")


@router.get("/login", response_model=OAuthLoginResponse)
def login_x(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    oauth_service: XOAuthService = Depends(get_x_oauth_service),
) -> OAuthLoginResponse:
    try:
        authorization_url = oauth_service.build_login_url(current_user.id)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return OAuthLoginResponse(authorization_url=authorization_url)


@router.get("/callback")
def callback_x(
    code: str | None = Query(default=None, min_length=1),
    state: str = Query(min_length=1),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
    oauth_service: XOAuthService = Depends(get_x_oauth_service),
) -> RedirectResponse:
    if error:
        return _frontend_redirect(
            oauth="x",
            status="error",
            message="Autorizacao recusada pelo provedor.",
        )
    if code is None:
        return _frontend_redirect(
            oauth="x",
            status="error",
            message="Authorization code ausente.",
        )

    try:
        account = oauth_service.complete_callback(state=state, code=code)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        return _frontend_redirect(oauth="x", status="error", message=exc.message)

    return _frontend_redirect(
        oauth="x",
        status="connected",
        account_id=str(account.id),
    )
