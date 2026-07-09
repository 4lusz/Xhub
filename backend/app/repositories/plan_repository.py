"""Repository para o model Plan."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    """Acesso a dados dos planos de assinatura."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, Plan)

    def get_by_name(self, name: str) -> Plan | None:
        statement = select(Plan).where(Plan.name == name)
        return self.db.scalars(statement).first()

    def list_ordered_by_price(self) -> Sequence[Plan]:
        statement = select(Plan).order_by(Plan.price.asc())
        return self.db.scalars(statement).all()
