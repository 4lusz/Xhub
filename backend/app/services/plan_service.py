"""Service de planos de assinatura."""

import uuid
from collections.abc import Sequence

from app.domain.plans import OFFICIAL_PLANS
from app.models.plan import Plan
from app.repositories.plan_repository import PlanRepository
from app.services.base_service import BaseService


class PlanService(BaseService[Plan]):
    def __init__(self, plan_repository: PlanRepository) -> None:
        super().__init__(plan_repository)
        self.plan_repository = plan_repository

    def get_plan(self, plan_id: uuid.UUID) -> Plan | None:
        return self.plan_repository.get(plan_id)

    def get_by_name(self, name: str) -> Plan | None:
        return self.plan_repository.get_by_name(name)

    def list_plans(self) -> Sequence[Plan]:
        return self.plan_repository.list_ordered_by_price()

    def sync_official_plans(self) -> Sequence[Plan]:
        plans: list[Plan] = []
        for official_plan in OFFICIAL_PLANS:
            plan = self.plan_repository.get_by_name(official_plan.name)
            data = {
                "name": official_plan.name,
                "max_accounts": official_plan.max_accounts,
                "max_posts_month": official_plan.max_posts_month,
            }

            if plan is None:
                plan = self.plan_repository.create(
                    {**data, "price": official_plan.default_price}
                )
            else:
                plan = self.plan_repository.update(plan, data)

            plans.append(plan)

        return plans

    def update_plan(
        self,
        plan_id: uuid.UUID,
        *,
        price,
        max_accounts: int,
        max_posts_month: int,
    ) -> Plan:
        plan = self.ensure_exists(plan_id, message="Plano nao encontrado.")


        return self.plan_repository.update(
            plan,
            {
                "price": price,
                "max_accounts": max_accounts,
                "max_posts_month": max_posts_month
            },
        )
