"""Rotas de autenticacao da aplicacao.

Correcao critica (auditoria item 2): o XHub NAO possui auto cadastro de
usuarios -- toda conta e criada exclusivamente por um administrador
(via `POST /admin/users`, que ja exige a escolha explicita do plano e
cria a `Subscription` correspondente na mesma transacao). O endpoint
publico `POST /auth/register` foi removido: ele criava usuarios sem
nenhuma assinatura associada, contas que falhavam imediatamente em
qualquer acao relevante do produto, e contradizia a regra de negocio
ja documentada em `app.routes.admin`.

Correcao (auditoria item 11): `/auth/login` agora tambem emite um
refresh token, e `/auth/refresh` (renovar sessao sem senha) e
`/auth/logout` (revogar o refresh token) foram adicionados -- antes,
`JWT_REFRESH_TOKEN_EXPIRE_DAYS` existia em `Settings` mas nao havia
nenhum fluxo de renovacao, forcando novo login por senha a cada 30
minutos (expiracao do access token).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth.dependencies import get_auth_service
from app.core.exceptions import (
    BaseAppException,
    ConflictException,
    UnauthorizedException,
    ValidationException,
)
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    raise HTTPException(
        status_code=status_code,
        detail=exc.message,
        headers=headers,
    ) from exc


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        user = auth_service.authenticate(
            email=form_data.username,
            password=form_data.password,
        )
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.issue_refresh_token(user)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Renova a sessao sem exigir senha novamente, usando um refresh
    token ainda valido (nao expirado, nao revogado). O token usado e
    revogado e um novo e emitido (rotacao -- ver `AuthService`)."""
    try:
        user, new_refresh_token = auth_service.rotate_refresh_token(
            data.refresh_token
        )
        access_token = auth_service.create_access_token(user)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: RefreshRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Revoga o refresh token informado. O access token JWT em uso
    continua valido ate expirar naturalmente (stateless, por design) --
    revogar o refresh token impede que a sessao seja renovada depois
    que ele expirar."""
    auth_service.revoke_refresh_token(data.refresh_token)
    db.commit()
