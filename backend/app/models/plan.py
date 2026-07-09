"""Model Plan -- planos de assinatura oferecidos pelo XHub."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.subscription import Subscription


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    max_accounts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_posts_month: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")

    def __repr__(self) -> str:
        return f"<Plan id={self.id} name={self.name!r}>"
