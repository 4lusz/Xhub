"""Objetos de contexto usados por regras de dominio puras."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import SubscriptionStatus, UserRole


@dataclass(frozen=True)
class UserContext:
    id: uuid.UUID
    role: UserRole
    is_blocked: bool = False


@dataclass(frozen=True)
class PlanLimits:
    max_accounts: int
    max_posts_month: int


@dataclass(frozen=True)
class PlanUsage:
    connected_accounts: int
    used_posts: int
    extra_posts: int = 0


@dataclass(frozen=True)
class SubscriptionContext:
    status: SubscriptionStatus
    expires_at: datetime
    plan_limits: PlanLimits
    usage: PlanUsage
