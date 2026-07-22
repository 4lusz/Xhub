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
from pydantic import BaseModel, Field

from app.auth.dependencies import (
    get_auth_service,
    get_current_admin,
    get_current_user,
    get_current_user_for_password_change,
    get_user_service,
)
from app.core.exceptions import (
    BaseAppException,
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
    ValidationException,
)
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Primeiro acesso obrigatorio (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
    # o login e SEMPRE aceito normalmente (mesmo com senha temporaria);
    # este campo e o sinal para o frontend redirecionar para a tela de
    # troca de senha ANTES de tentar qualquer outra rota protegida,
    # sem precisar de uma chamada extra (que seria bloqueada com 428).
    must_change_password: bool


class SecondFactorRequiredResponse(BaseModel):
    """Retornado por `POST /auth/login` no lugar de `TokenResponse`
    quando o usuario (hoje, sempre um administrador -- ver
    docs/AUDITORIA_SEGURANCA.md) configurou uma pergunta de seguranca.
    `pending_token` tem validade curta (5 minutos) e so serve para
    `POST /auth/verify-security-answer` -- nunca e um token de acesso
    valido em nenhuma outra rota (ver
    `app.auth.dependencies._resolve_authenticated_user`)."""

    requires_second_factor: bool = True
    pending_token: str
    question: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_blocked: bool
    must_change_password: bool
    # Texto da pergunta configurada (nunca a resposta) -- `None` quando
    # o usuario nao tem segundo fator configurado. Usado pela tela de
    # Configuracoes para mostrar o estado atual.
    security_question: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class VerifySecurityAnswerRequest(BaseModel):
    pending_token: str
    answer: str = Field(min_length=1, max_length=200)


class SetSecurityQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=200)


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ForbiddenException):
        # Correcao (auditoria funcional): faltava esta branch -- antes,
        # um `ForbiddenException` (ex.: bloqueio de conta em
        # `AuthService.authenticate`/`rotate_refresh_token`) caia no
        # default 400, em vez do 403 usado para bloqueio em toda a
        # demais aplicacao (ver `app.auth.dependencies`).
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    raise HTTPException(
        status_code=status_code,
        detail=exc.message,
        headers=headers,
    ) from exc


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_blocked=user.is_blocked,
        must_change_password=user.must_change_password,
        security_question=user.security_question,
    )


@router.post("/login", response_model=TokenResponse | SecondFactorRequiredResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse | SecondFactorRequiredResponse:
    try:
        user = auth_service.authenticate(
            email=form_data.username,
            password=form_data.password,
        )

        # Segundo fator simples de login (ver docs/AUDITORIA_SEGURANCA.md):
        # so entra em jogo para quem configurou uma pergunta de
        # seguranca (hoje, administradores) -- login continua normal,
        # em uma unica etapa, para todo o resto. Emite um token
        # pendente de validade curta em vez do par access+refresh; o
        # login so se completa em `POST /auth/verify-security-answer`.
        if auth_service.requires_second_factor(user):
            pending_token = auth_service.issue_pending_2fa_token(user)
            db.commit()
            return SecondFactorRequiredResponse(
                pending_token=pending_token,
                question=user.security_question,
            )

        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.issue_refresh_token(user)
        must_change_password = user.must_change_password
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=must_change_password,
    )


@router.post("/verify-security-answer", response_model=TokenResponse)
def verify_security_answer(
    data: VerifySecurityAnswerRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Segunda etapa do login para quem tem pergunta de seguranca
    configurada -- completa com o mesmo par access+refresh de um login
    normal, uma vez confirmada a resposta certa."""
    try:
        user = auth_service.verify_security_answer(
            pending_token=data.pending_token,
            answer=data.answer,
        )
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.issue_refresh_token(user)
        must_change_password = user.must_change_password
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=must_change_password,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = user_service.get_user(current_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    return _to_user_response(user)


@router.post("/change-password", response_model=UserResponse)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_for_password_change),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Conclui o primeiro acesso obrigatorio (ver
    docs/ROADMAP_PRIMEIRO_ACESSO.md): troca a senha temporaria pela
    senha definitiva escolhida pelo usuario. Unica rota protegida
    acessivel enquanto `must_change_password=True` (ver
    `get_current_user_for_password_change`) -- depois desta chamada,
    o campo volta a `False` e todas as demais rotas sao liberadas
    normalmente."""
    try:
        user = user_service.complete_first_access(
            user_id=current_user.id,
            new_password=data.new_password,
        )
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


@router.post("/security-question", response_model=UserResponse)
def set_security_question(
    data: SetSecurityQuestionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Configura (ou substitui) a pergunta de seguranca do proprio
    administrador autenticado -- restrito a administradores
    (`get_current_admin`), ver docs/AUDITORIA_SEGURANCA.md."""
    try:
        user = user_service.set_security_question(
            current_admin.id, question=data.question, answer=data.answer
        )
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


@router.delete("/security-question", response_model=UserResponse)
def remove_security_question(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Remove a pergunta de seguranca -- o proprio administrador volta
    a autenticar so com email+senha."""
    try:
        user = user_service.clear_security_question(current_admin.id)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


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
        user, new_refresh_token = auth_service.rotate_refresh_token(data.refresh_token)
        access_token = auth_service.create_access_token(user)
        must_change_password = user.must_change_password
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        must_change_password=must_change_password,
    )


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
