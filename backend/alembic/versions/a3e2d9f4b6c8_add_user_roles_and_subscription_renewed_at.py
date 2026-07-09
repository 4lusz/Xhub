"""add user roles and subscription renewed_at

Revision ID: a3e2d9f4b6c8
Revises: 7c4b7dfb9c21
Create Date: 2026-07-07 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a3e2d9f4b6c8"
down_revision: Union[str, None] = "7c4b7dfb9c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role_enum = postgresql.ENUM("CLIENT", "ADMIN", name="user_role")


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM(
                "CLIENT",
                "ADMIN",
                name="user_role",
                create_type=False,
            ),
            server_default="CLIENT",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "subscriptions",
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "renewed_at")
    op.drop_column("users", "is_blocked")
    op.drop_column("users", "role")

    bind = op.get_bind()
    user_role_enum.drop(bind, checkfirst=True)
