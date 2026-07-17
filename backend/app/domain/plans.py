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

# Maior `max_accounts` entre todos os planos do catalogo oficial acima
# (hoje: Agencia, 100). Usado como teto de validacao de entrada (ver
# `CreatePostRequest`/`IntelligentPublicationPreviewRequest`,
# `twitter_account_ids`) -- nenhum usuario real pode ter mais contas
# conectadas do que o maior plano permite, entao qualquer lista maior
# que isso e necessariamente invalida (e, sem um teto, um vetor de
# negacao de servico: cada id da lista gera uma consulta sequencial ao
# banco antes de qualquer validacao de posse). Deriva do catalogo em vez
# de um numero fixo para nunca ficar dessincronizado se um plano maior
# for adicionado.
MAX_ACCOUNTS_ACROSS_PLANS = max(plan.max_accounts for plan in OFFICIAL_PLANS)
