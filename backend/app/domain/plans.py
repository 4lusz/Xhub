"""Catalogo oficial de planos do XHub v1."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OfficialPlan:
    name: str
    max_accounts: int
    max_posts_month: int
    default_price: Decimal = Decimal("0.00")


PLAN_CREATOR = "Creator"
PLAN_START = "Start"
PLAN_PRO = "Pro"
PLAN_AGENCY = "Agencia"

OFFICIAL_PLANS: tuple[OfficialPlan, ...] = (
    OfficialPlan(name=PLAN_CREATOR, max_accounts=5, max_posts_month=300),
    OfficialPlan(name=PLAN_START, max_accounts=15, max_posts_month=1200),
    OfficialPlan(name=PLAN_PRO, max_accounts=50, max_posts_month=6000),
    OfficialPlan(name=PLAN_AGENCY, max_accounts=100, max_posts_month=15000),
)
