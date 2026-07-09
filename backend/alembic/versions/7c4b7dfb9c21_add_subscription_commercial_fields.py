"""add subscription commercial fields

Revision ID: 7c4b7dfb9c21
Revises: 425b5fb53a66
Create Date: 2026-07-07 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7c4b7dfb9c21"
down_revision: Union[str, None] = "425b5fb53a66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

subscription_status_enum = postgresql.ENUM(
    "ACTIVE",
    "EXPIRED",
    "BLOCKED",
    name="subscription_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    subscription_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "subscriptions",
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "EXPIRED",
                "BLOCKED",
                name="subscription_status",
                create_type=False,
            ),
            server_default="ACTIVE",
            nullable=False,
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("used_posts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "subscriptions",
        sa.Column("extra_posts", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "extra_posts")
    op.drop_column("subscriptions", "used_posts")
    op.drop_column("subscriptions", "status")

    bind = op.get_bind()
    subscription_status_enum.drop(bind, checkfirst=True)
