"""Politicas de negocio puras do XHub.

Este modulo nao acessa banco, HTTP, FastAPI, repositories ou services.
"""

from datetime import UTC, datetime

from app.core.exceptions import ConflictException, ForbiddenException
from app.domain.contexts import PlanLimits, SubscriptionContext, UserContext
from app.domain.enums import SubscriptionStatus, UserRole

# ---------------------------------------------------------------------- #
# Publicacao Inteligente (ver docs/ROADMAP_PUBLICACAO_INTELIGENTE.md)
# ---------------------------------------------------------------------- #
# Regra de negocio oficial por quantidade de contas selecionadas:
# - 1 conta: publicar texto original, sem chamar IA.
# - 2 a 4 contas: variacao opcional (ativada por padrao no frontend).
# - 5+ contas: variacao obrigatoria, sem fallback automatico para o
#   mesmo texto.
# Constantes compartilhadas entre `PostService` (validacao na criacao
# do post) e `AIContentVariationService` (estrategia de geracao), para
# que as duas camadas nunca divirjam sobre o limiar.
OPTIONAL_VARIATION_MAX_ACCOUNTS = 4
MANDATORY_VARIATION_ACCOUNT_THRESHOLD = 5


def is_variation_mandatory(account_count: int) -> bool:
    return account_count >= MANDATORY_VARIATION_ACCOUNT_THRESHOLD


def ensure_user_not_blocked(user: UserContext) -> None:
    """Bloqueio de CONTA: usuario nao pode logar nem realizar nenhuma acao,
    independente do estado da assinatura. Ver `ensure_subscription_active`
    para o bloqueio de ASSINATURA (mais restrito, nao afeta login)."""
    if user.is_blocked:
        raise ForbiddenException("Usuario bloqueado.")


def ensure_admin(user: UserContext) -> None:
    ensure_user_not_blocked(user)
    if user.role is not UserRole.ADMIN:
        raise ForbiddenException("Acao permitida apenas para administradores.")


def ensure_client(user: UserContext) -> None:
    ensure_user_not_blocked(user)
    if user.role is not UserRole.CLIENT:
        raise ForbiddenException("Acao permitida apenas para clientes.")


def is_subscription_active(
    subscription: SubscriptionContext,
    *,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now(UTC)
    return (
        subscription.status is SubscriptionStatus.ACTIVE
        and subscription.expires_at >= current_time
    )


def ensure_subscription_active(
    subscription: SubscriptionContext,
    *,
    now: datetime | None = None,
) -> None:
    """Bloqueio de ASSINATURA: restringe o uso do plano (consumo de posts,
    conexao de contas do X), mas nao impede login nem acesso ao XHub. E um
    conceito independente do bloqueio de CONTA (`ensure_user_not_blocked`),
    que e mais amplo e proibe qualquer acao do usuario."""
    if not is_subscription_active(subscription, now=now):
        raise ForbiddenException("Assinatura inativa, expirada ou bloqueada.")


def get_available_posts(subscription: SubscriptionContext) -> int:
    total_posts = (
        subscription.plan_limits.max_posts_month
        + subscription.usage.extra_posts
    )
    return max(total_posts - subscription.usage.used_posts, 0)


def ensure_sufficient_posts(
    subscription: SubscriptionContext,
    *,
    required_posts: int,
) -> None:
    if required_posts <= 0:
        raise ConflictException("Consumo de posts deve ser maior que zero.")

    if get_available_posts(subscription) < required_posts:
        raise ForbiddenException("Saldo de posts insuficiente.")


def can_connect_account(subscription: SubscriptionContext) -> bool:
    return (
        subscription.usage.connected_accounts
        < subscription.plan_limits.max_accounts
    )


def ensure_can_connect_account(
    subscription: SubscriptionContext,
    *,
    now: datetime | None = None,
) -> None:
    ensure_subscription_active(subscription, now=now)
    if not can_connect_account(subscription):
        raise ForbiddenException("Limite de contas do plano atingido.")


def should_block_new_connections_after_plan_change(
    *,
    connected_accounts: int,
    new_plan_limits: PlanLimits,
) -> bool:
    return connected_accounts >= new_plan_limits.max_accounts
