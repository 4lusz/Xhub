"""Regras de dominio puras do XHub."""

from app.domain.contexts import (
    PlanLimits,
    PlanUsage,
    SubscriptionContext,
    UserContext,
)
from app.domain.enums import PublicationContentType, SubscriptionStatus, UserRole
from app.domain.policies import (
    can_connect_account,
    ensure_admin,
    ensure_can_connect_account,
    ensure_client,
    ensure_subscription_active,
    ensure_sufficient_posts,
    ensure_user_not_blocked,
    get_available_posts,
    is_subscription_active,
    should_block_new_connections_after_plan_change,
)
from app.domain.plans import (
    OFFICIAL_PLANS,
    PLAN_AGENCY,
    PLAN_CREATOR,
    PLAN_PRO,
    PLAN_START,
    OfficialPlan,
)
from app.domain.publication_cost import (
    DEFAULT_PUBLICATION_COST_POLICY,
    PublicationCostPolicy,
    calculate_publication_cost,
)

__all__ = [
    "PlanLimits",
    "PlanUsage",
    "SubscriptionContext",
    "UserContext",
    "SubscriptionStatus",
    "UserRole",
    "PublicationContentType",
    "DEFAULT_PUBLICATION_COST_POLICY",
    "PublicationCostPolicy",
    "calculate_publication_cost",
    "OFFICIAL_PLANS",
    "PLAN_AGENCY",
    "PLAN_CREATOR",
    "PLAN_PRO",
    "PLAN_START",
    "OfficialPlan",
    "can_connect_account",
    "ensure_admin",
    "ensure_can_connect_account",
    "ensure_client",
    "ensure_subscription_active",
    "ensure_sufficient_posts",
    "ensure_user_not_blocked",
    "get_available_posts",
    "is_subscription_active",
    "should_block_new_connections_after_plan_change",
]
