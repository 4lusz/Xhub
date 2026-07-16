"""Rotas administrativas do XHub."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_audit_log_service,
    get_current_admin,
    get_plan_service,
    get_post_service,
    get_subscription_service,
    get_user_service,
)
from app.core.exceptions import (
    BaseAppException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.database.session import get_db
from app.models.enums import (
    AuditAction,
    PostAccountStatus,
    PostStatus,
    SubscriptionStatus,
    UserRole,
)
from app.models.audit_log import AuditLog
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.post_service import PostService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.plan_service import PlanService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


class RegisterUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CLIENT
    # Fluxo correto do XHub: nao existe auto cadastro nem plano padrao
    # implicito. O administrador escolhe explicitamente o plano e a
    # vigencia da assinatura no momento em que cria a conta.
    plan_id: uuid.UUID
    subscription_expires_at: datetime


class ChangeRoleRequest(BaseModel):
    role: UserRole


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    is_blocked: bool


class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    max_accounts: int
    max_posts_month: int


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: SubscriptionStatus
    expires_at: datetime
    renewed_at: datetime | None
    used_posts: int
    extra_posts: int
    # Consumo derivado (auditoria: "visualizacao do consumo do usuario"
    # para o administrador) -- mesma politica de dominio usada em
    # `GET /me/subscription` para o proprio cliente, agora tambem
    # exposta ao admin em toda resposta de assinatura (consulta e apos
    # cada acao de renovar/bloquear/expirar/creditos extras).
    available_posts: int
    used_accounts: int
    plan: PlanResponse


class AuditLogResponse(BaseModel):
    id: str
    action: AuditAction
    # Nome do autor da acao quando ainda existir (o FK usa ON DELETE SET
    # NULL, entao acoes de usuarios ja removidos preservam o registro mas
    # perdem a referencia ao autor).
    actor_user_id: str | None
    actor_name: str | None
    target_type: str | None
    target_id: str | None
    description: str | None
    details: dict | None
    created_at: datetime


class AdminPostAccountResponse(BaseModel):
    twitter_account_id: str
    username: str
    status: PostAccountStatus
    x_post_id: str | None
    # Motivo exato da falha (status HTTP + corpo da resposta da API do
    # X, preservado por `XOAuthClient.publish_post`) -- so exposto aqui,
    # na visao administrativa, para auditoria e suporte. Nao aparece em
    # `GET /posts` (visao do cliente, ver `app/routes/post.py`).
    error_message: str | None


class AdminPostResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    # Conteudo do post (`Post.text`) NAO e exposto aqui de proposito --
    # privacidade do usuario. O administrador ve apenas status (do post
    # e por conta) e o motivo de falha quando houver, nunca o que foi
    # escrito.
    status: PostStatus
    created_at: datetime
    accounts: list[AdminPostAccountResponse] = Field(default_factory=list)


class AdminStatsResponse(BaseModel):
    """Metricas agregadas da plataforma para o dashboard administrativo
    (somente leitura). A gestao de usuarios/planos/assinaturas continua
    nas rotas dedicadas -- este endpoint apenas agrega contagens."""

    total_users: int
    active_subscriptions: int
    blocked_subscriptions: int
    expired_subscriptions: int
    total_posts: int
    published_posts: int


class UpdatePlanRequest(BaseModel):
    price: float = Field(gt=0)
    max_accounts: int = Field(gt=0)
    max_posts_month: int = Field(gt=0)


class RenewSubscriptionRequest(BaseModel):
    expires_at: datetime
    plan_id: uuid.UUID | None = None


class ExtraPostsRequest(BaseModel):
    amount: int = Field(gt=0)


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
        is_blocked=user.is_blocked,
    )


def _to_subscription_response(
    subscription: Subscription,
    subscription_service: SubscriptionService,
) -> SubscriptionResponse:
    context = subscription_service.to_domain_context(subscription)

    return SubscriptionResponse(
        id=str(subscription.id),
        user_id=str(subscription.user_id),
        plan_id=str(subscription.plan_id),
        status=subscription.status,
        expires_at=subscription.expires_at,
        renewed_at=subscription.renewed_at,
        used_posts=subscription.used_posts,
        extra_posts=subscription.extra_posts,
        available_posts=subscription_service.get_available_posts(subscription),
        used_accounts=context.usage.connected_accounts,
        plan=_to_plan_response(subscription.plan),
    )


def _to_plan_response(plan: Plan) -> PlanResponse:
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        price=float(plan.price),
        max_accounts=plan.max_accounts,
        max_posts_month=plan.max_posts_month,
    )


def _to_admin_post_response(post) -> AdminPostResponse:
    return AdminPostResponse(
        id=str(post.id),
        user_id=str(post.user_id),
        user_name=post.user.name,
        user_email=post.user.email,
        status=post.status,
        created_at=post.created_at,
        accounts=[
            AdminPostAccountResponse(
                twitter_account_id=str(account.twitter_account_id),
                username=account.twitter_account.username,
                status=account.status,
                x_post_id=account.x_post_id,
                error_message=account.error_message,
            )
            for account in post.post_accounts
        ],
    )


def _to_audit_log_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(log.id),
        action=log.action,
        actor_user_id=str(log.actor_user_id) if log.actor_user_id is not None else None,
        actor_name=log.actor.name if log.actor is not None else None,
        target_type=log.target_type,
        target_id=str(log.target_id) if log.target_id is not None else None,
        description=log.description,
        details=log.details,
        created_at=log.created_at,
    )


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, ConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    raise HTTPException(
        status_code=status_code,
        detail=exc.message,
        headers=headers,
    ) from exc


@router.get("/posts", response_model=list[AdminPostResponse])
def list_all_posts(
    status_filter: PostStatus | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
    post_service: PostService = Depends(get_post_service),
) -> list[AdminPostResponse]:
    """Posts de todos os usuarios, com o detalhamento por conta
    (incluindo `error_message` -- motivo exato retornado pela API do X
    em caso de falha) -- somente leitura, para auditoria e suporte.
    Nao substitui nem altera nada do fluxo de criacao/publicacao de
    posts, que continua exclusivamente em `app/routes/post.py`."""
    posts = post_service.list_all_posts(
        status=status_filter, offset=offset, limit=limit
    )
    return [_to_admin_post_response(post) for post in posts]


@router.get("/stats", response_model=AdminStatsResponse)
def get_stats(
    _: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    post_service: PostService = Depends(get_post_service),
) -> AdminStatsResponse:
    """Visao agregada da plataforma (total de usuarios, assinaturas por
    status e volume de posts)."""
    return AdminStatsResponse(
        total_users=user_service.count(),
        active_subscriptions=subscription_service.count_by_status(
            SubscriptionStatus.ACTIVE
        ),
        blocked_subscriptions=subscription_service.count_by_status(
            SubscriptionStatus.BLOCKED
        ),
        expired_subscriptions=subscription_service.count_by_status(
            SubscriptionStatus.EXPIRED
        ),
        total_posts=post_service.count(),
        published_posts=post_service.count_by_status(PostStatus.PUBLISHED),
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_admin),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> list[AuditLogResponse]:
    """Trilha de auditoria administrativa, mais recentes primeiro
    (paginada). Somente leitura -- os registros sao append-only (ver
    `AuditLogRepository`)."""
    logs = audit_log_service.list_recent(offset=offset, limit=limit)
    return [_to_audit_log_response(log) for log in logs]


@router.get("/users", response_model=list[UserResponse])
def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> list[UserResponse]:
    users = user_service.list_users(
        offset=offset,
        limit=limit,
    )
    return [_to_user_response(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    _: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        user = user_service.get_user(user_id)

        if user is None:
            raise NotFoundException("Usuario nao encontrado.")

    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_user_response(user)


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
)
def get_subscription(
    subscription_id: uuid.UUID,
    _: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.get(
    "/users/{user_id}/subscription",
    response_model=SubscriptionResponse,
)
def get_user_subscription(
    user_id: uuid.UUID,
    _: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.get_current_subscription(user_id)
        if subscription is None:
            raise NotFoundException("Assinatura nao encontrada para esse usuario.")
    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    data: RegisterUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> UserResponse:
    try:
        user = user_service.create_user(
            name=data.name,
            email=data.email,
            password=data.password,
            role=data.role,
        )

        # Fluxo correto do XHub: nao ha auto cadastro nem assinatura
        # trial automatica. Toda conta e criada pelo administrador, que
        # escolhe explicitamente o plano; a Subscription correspondente
        # e criada aqui, na mesma transacao do usuario (commit unico
        # abaixo -- se qualquer etapa falhar, tudo e revertido).
        subscription_service.create_subscription(
            user_id=user.id,
            plan_id=data.plan_id,
            expires_at=data.subscription_expires_at,
        )

        audit_log_service.record(
            action=AuditAction.USER_CREATED,
            actor_user_id=current_admin.id,
            target_type="user",
            target_id=user.id,
            description="Usuario criado.",
            details={
                "role": data.role.value,
                "plan_id": str(data.plan_id) if data.plan_id is not None else None,
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


@router.post("/users/{user_id}/block", response_model=UserResponse)
def block_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> UserResponse:
    try:
        user = user_service.block_user(user_id)

        audit_log_service.record(
            action=AuditAction.USER_BLOCKED,
            actor_user_id=current_admin.id,
            target_type="user",
            target_id=user.id,
            description="Usuario bloqueado.",
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


@router.post("/users/{user_id}/unblock", response_model=UserResponse)
def unblock_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> UserResponse:
    try:
        user = user_service.unblock_user(user_id)

        audit_log_service.record(
            action=AuditAction.USER_UNBLOCKED,
            actor_user_id=current_admin.id,
            target_type="user",
            target_id=user.id,
            description="Usuario desbloqueado.",
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def change_role(
    user_id: uuid.UUID,
    data: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> UserResponse:
    try:
        user = user_service.change_role(
            user_id=user_id,
            role=data.role,
        )

        audit_log_service.record(
            action=AuditAction.USER_ROLE_CHANGED,
            actor_user_id=current_admin.id,
            target_type="user",
            target_id=user.id,
            description="Role do usuario alterada.",
            details={
                "role": data.role.value,
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_user_response(user)

    # ==========================================


# SUBSCRIPTIONS
# ==========================================


@router.post(
    "/subscriptions/{subscription_id}/renew",
    response_model=SubscriptionResponse,
)
def renew_subscription(
    subscription_id: uuid.UUID,
    data: RenewSubscriptionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.renew_subscription(
            subscription_id=subscription_id,
            expires_at=data.expires_at,
            plan_id=data.plan_id,
        )

        audit_log_service.record(
            action=AuditAction.SUBSCRIPTION_RENEWED,
            actor_user_id=current_admin.id,
            target_type="subscription",
            target_id=subscription.id,
            description="Assinatura renovada.",
            details={
                "plan_id": str(data.plan_id) if data.plan_id is not None else None,
                "expires_at": data.expires_at.isoformat(),
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.post(
    "/subscriptions/{subscription_id}/block",
    response_model=SubscriptionResponse,
)
def block_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.block_subscription(
            subscription_id=subscription_id,
        )

        audit_log_service.record(
            action=AuditAction.SUBSCRIPTION_BLOCKED,
            actor_user_id=current_admin.id,
            target_type="subscription",
            target_id=subscription.id,
            description="Assinatura bloqueada.",
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.post(
    "/subscriptions/{subscription_id}/expire",
    response_model=SubscriptionResponse,
)
def expire_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.expire_subscription(
            subscription_id=subscription_id,
        )

        audit_log_service.record(
            action=AuditAction.SUBSCRIPTION_EXPIRED,
            actor_user_id=current_admin.id,
            target_type="subscription",
            target_id=subscription.id,
            description="Assinatura expirada.",
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.post(
    "/subscriptions/{subscription_id}/extra-posts/add",
    response_model=SubscriptionResponse,
)
def add_extra_posts(
    subscription_id: uuid.UUID,
    data: ExtraPostsRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.add_extra_posts(
            subscription_id=subscription_id,
            amount=data.amount,
        )

        audit_log_service.record(
            action=AuditAction.EXTRA_POSTS_ADDED,
            actor_user_id=current_admin.id,
            target_type="subscription",
            target_id=subscription.id,
            description="Posts extras adicionados.",
            details={
                "amount": data.amount,
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)


@router.post(
    "/subscriptions/{subscription_id}/extra-posts/remove",
    response_model=SubscriptionResponse,
)
def remove_extra_posts(
    subscription_id: uuid.UUID,
    data: ExtraPostsRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> SubscriptionResponse:
    try:
        subscription = subscription_service.remove_extra_posts(
            subscription_id=subscription_id,
            amount=data.amount,
        )

        audit_log_service.record(
            action=AuditAction.EXTRA_POSTS_REMOVED,
            actor_user_id=current_admin.id,
            target_type="subscription",
            target_id=subscription.id,
            description="Posts extras removidos.",
            details={
                "amount": data.amount,
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_subscription_response(subscription, subscription_service)

    # ==========================================


# PLANS
# ==========================================


@router.get(
    "/plans",
    response_model=list[PlanResponse],
)
def list_plans(
    _: User = Depends(get_current_admin),
    plan_service: PlanService = Depends(get_plan_service),
) -> list[PlanResponse]:
    plans = plan_service.list_plans()
    return [_to_plan_response(plan) for plan in plans]


@router.post(
    "/plans/sync",
    response_model=list[PlanResponse],
)
def sync_plans(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    plan_service: PlanService = Depends(get_plan_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> list[PlanResponse]:
    """Sincroniza o catalogo oficial de planos (`app.domain.plans`) sob
    demanda. Complementa a sincronizacao automatica que ja acontece no
    startup da aplicacao (ver `app.core.bootstrap`) -- util quando o
    catalogo oficial ganha um novo plano com a aplicacao ja no ar, sem
    exigir reinicio do processo nem insercao manual no banco (auditoria
    item 1)."""
    try:
        plans = plan_service.sync_official_plans()

        audit_log_service.record(
            action=AuditAction.PLAN_SYNCED,
            actor_user_id=current_admin.id,
            target_type="plan",
            target_id=None,
            description="Catalogo oficial de planos sincronizado manualmente.",
            details={"plans_count": len(plans)},
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return [_to_plan_response(plan) for plan in plans]


@router.patch(
    "/plans/{plan_id}",
    response_model=PlanResponse,
)
def update_plan(
    plan_id: uuid.UUID,
    data: UpdatePlanRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    plan_service: PlanService = Depends(get_plan_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> PlanResponse:
    try:
        plan = plan_service.update_plan(
            plan_id=plan_id,
            price=data.price,
            max_accounts=data.max_accounts,
            max_posts_month=data.max_posts_month,
        )

        audit_log_service.record(
            action=AuditAction.PLAN_UPDATED,
            actor_user_id=current_admin.id,
            target_type="plan",
            target_id=plan.id,
            description="Plano atualizado.",
            details={
                "price": data.price,
                "max_accounts": data.max_accounts,
                "max_posts_month": data.max_posts_month,
            },
        )

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)

    return _to_plan_response(plan)
