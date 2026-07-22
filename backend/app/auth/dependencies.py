"""Dependencies de autenticacao para rotas FastAPI."""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.core.exceptions import (
    ForbiddenException,
    PasswordChangeRequiredException,
    UnauthorizedException,
)
from app.database.session import get_db
from app.domain.contexts import UserContext
from app.domain.enums import UserRole as DomainUserRole
from app.domain.policies import (
    ensure_admin,
    ensure_client,
    ensure_password_change_not_required,
    ensure_user_not_blocked,
)
from app.models.user import User
from app.integrations.groq_client import GroqClient
from app.oauth.oauth_client import XOAuthClient
from app.oauth.oauth_service import XOAuthService
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.oauth_session_repository import OAuthSessionRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.repositories.account_metric_snapshot_repository import (
    AccountMetricSnapshotRepository,
)
from app.repositories.jitter_settings_repository import JitterSettingsRepository
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_media_repository import PostMediaRepository
from app.repositories.post_metric_snapshot_repository import PostMetricSnapshotRepository
from app.repositories.post_repository import PostRepository
from app.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.ai_content_variation_service import AIContentVariationService
from app.services.jitter_service import JitterService
from app.services.media_service import MediaService
from app.services.metrics_service import MetricsService
from app.services.post_service import PostService
from app.services.scheduled_post_service import ScheduledPostService
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService
from app.services.plan_service import PlanService
from app.services.subscription_service import SubscriptionService
from app.services.twitter_account_service import TwitterAccountService
from app.services.user_service import UserService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _credentials_exception(
    message: str = "Nao foi possivel validar credenciais.",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db), RefreshTokenRepository(db))


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db))


def get_plan_service(db: Session = Depends(get_db)) -> PlanService:
    return PlanService(
        PlanRepository(db),
    )


def get_subscription_service(
    db: Session = Depends(get_db),
) -> SubscriptionService:
    return SubscriptionService(
        SubscriptionRepository(db),
        UserRepository(db),
        PlanRepository(db),
    )


def get_twitter_account_service(db: Session = Depends(get_db)) -> TwitterAccountService:
    return TwitterAccountService(
        TwitterAccountRepository(db),
        UserRepository(db),
    )


def get_media_service(db: Session = Depends(get_db)) -> MediaService:
    return MediaService(PostMediaRepository(db))


def get_jitter_service(db: Session = Depends(get_db)) -> JitterService:
    return JitterService(JitterSettingsRepository(db))


def get_post_service(
    db: Session = Depends(get_db),
) -> PostService:
    return PostService(
        post_repository=PostRepository(db),
        post_account_repository=PostAccountRepository(db),
        twitter_account_repository=TwitterAccountRepository(db),
        user_repository=UserRepository(db),
        x_oauth_client=XOAuthClient(),
        subscription_service=get_subscription_service(db),
        post_media_repository=PostMediaRepository(db),
        jitter_service=get_jitter_service(db),
    )


def get_metrics_service(db: Session = Depends(get_db)) -> MetricsService:
    return MetricsService(
        AccountMetricSnapshotRepository(db),
        PostMetricSnapshotRepository(db),
        TwitterAccountRepository(db),
        PostAccountRepository(db),
        XOAuthClient(),
    )


def get_scheduled_post_service(
    db: Session = Depends(get_db),
) -> ScheduledPostService:
    return ScheduledPostService(
        ScheduledPostRepository(db),
        PostRepository(db),
    )


def get_ai_content_variation_service(
    db: Session = Depends(get_db),
) -> AIContentVariationService:
    return AIContentVariationService(
        GroqClient(),
        TwitterAccountRepository(db),
    )


def get_x_oauth_service(
    db: Session = Depends(get_db),
    twitter_account_service: TwitterAccountService = Depends(
        get_twitter_account_service
    ),
    subscription_service: SubscriptionService = Depends(
    get_subscription_service,
    ),
) -> XOAuthService:
    return XOAuthService(
        oauth_client=XOAuthClient(),
        twitter_account_service=twitter_account_service,
        subscription_service=subscription_service,
        oauth_session_repository=OAuthSessionRepository(db),
    )


def get_audit_log_service(db: Session = Depends(get_db)) -> AuditLogService:
    """Fornece o service de auditoria para injecao em futuras rotas
    administrativas. Nenhuma rota usa esta dependency ainda."""
    return AuditLogService(AuditLogRepository(db))


def _resolve_authenticated_user(token: str, user_service: UserService) -> User:
    """Decodifica o token, carrega o usuario e garante que a CONTA nao
    esta bloqueada. NAO verifica primeiro acesso obrigatorio (ver
    `ensure_password_change_not_required`) -- usado tanto por
    `get_current_user` (que adiciona essa checagem por cima) quanto por
    `get_current_user_for_password_change` (que precisa funcionar
    exatamente enquanto a troca de senha ainda esta pendente, pois e a
    unica rota capaz de conclui-la)."""
    try:
        payload = decode_access_token(token)
    except UnauthorizedException as exc:
        raise _credentials_exception(exc.message) from exc

    # Correcao (auditoria de seguranca -- 2o fator de login, ver
    # docs/AUDITORIA_SEGURANCA.md): o token "pendente" emitido por
    # `AuthService.issue_pending_2fa_token` (apos senha correta, antes
    # da resposta de seguranca) tem a mesma estrutura de um access
    # token normal -- sem esta checagem explicita, ele seria aceito
    # aqui como um token de acesso valido, permitindo completar o login
    # sem nunca responder a pergunta de seguranca. So
    # `POST /auth/verify-security-answer` decodifica e aceita este
    # estagio; em qualquer outra rota, e sempre invalido.
    if payload.get("stage") == "pending_2fa":
        raise _credentials_exception("Token invalido.")

    subject = payload["sub"]

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _credentials_exception("Token invalido.") from exc

    user = user_service.get_user(user_id)
    if user is None:
        raise _credentials_exception("Usuario autenticado nao encontrado.")

    try:
        ensure_user_not_blocked(_to_user_context(user))
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc

    return user


def get_current_user_for_password_change(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Usado exclusivamente por `POST /auth/change-password` (ver
    docs/ROADMAP_PRIMEIRO_ACESSO.md). Deliberadamente NAO passa pelo
    gate de primeiro acesso obrigatorio de `get_current_user` -- e
    justamente o endpoint que permite conclui-lo."""
    return _resolve_authenticated_user(token, user_service)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    user = _resolve_authenticated_user(token, user_service)

    # Primeiro acesso obrigatorio (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
    # unico ponto de checagem, herdado automaticamente por toda rota
    # que depende de `get_current_user`, `get_current_client` ou
    # `get_current_admin` -- nenhuma rota protegida precisa de
    # alteracao individual. Mapeado para 428 (Precondition Required)
    # em vez de 401/403 para que o frontend saiba redirecionar para a
    # tela de troca de senha, em vez de tratar como sessao invalida ou
    # acesso negado generico.
    try:
        ensure_password_change_not_required(_to_user_context(user))
    except PasswordChangeRequiredException as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return user


def get_current_client(current_user: User = Depends(get_current_user)) -> User:
    try:
        ensure_client(_to_user_context(current_user))
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc

    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    try:
        ensure_admin(_to_user_context(current_user))
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc

    return current_user


def _to_user_context(user: User) -> UserContext:
    return UserContext(
        id=user.id,
        role=DomainUserRole(user.role.value),
        is_blocked=user.is_blocked,
        must_change_password=user.must_change_password,
    )