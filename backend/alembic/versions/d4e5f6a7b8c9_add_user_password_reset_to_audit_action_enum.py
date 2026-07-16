"""add USER_PASSWORD_RESET value to audit_action enum

Primeiro acesso obrigatorio (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
`POST /admin/users/{user_id}/reset-password` registra
`AuditAction.USER_PASSWORD_RESET` na mesma transacao da redefinicao --
mesma classe de correcao das migrations 9b2f6a1d7e4c e b4c5d6e7f8a9
(adicionar o valor ao enum nativo do Postgres ANTES do primeiro uso,
evitando o 500 "invalid input value for enum audit_action").

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-17 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_PASSWORD_RESET'")


def downgrade() -> None:
    bind = op.get_bind()

    in_use = bind.execute(
        sa.text("SELECT COUNT(*) FROM audit_logs WHERE action = 'USER_PASSWORD_RESET'")
    ).scalar_one()

    if in_use:
        raise RuntimeError(
            "Downgrade abortado: existem "
            f"{in_use} audit_logs com action USER_PASSWORD_RESET. "
            "audit_logs e append-only por regra de negocio -- nao remova "
            "esses registros para permitir o downgrade."
        )

    op.execute("ALTER TYPE audit_action RENAME TO audit_action_old")

    new_audit_action_enum = sa.Enum(
        "USER_BLOCKED",
        "USER_UNBLOCKED",
        "USER_ROLE_CHANGED",
        "SUBSCRIPTION_CREATED",
        "SUBSCRIPTION_RENEWED",
        "SUBSCRIPTION_BLOCKED",
        "SUBSCRIPTION_EXPIRED",
        "EXTRA_POSTS_ADDED",
        "EXTRA_POSTS_REMOVED",
        "PLAN_SYNCED",
        "TWITTER_ACCOUNT_CONNECTED",
        "TWITTER_ACCOUNT_DISCONNECTED",
        "OTHER",
        "USER_CREATED",
        "PLAN_UPDATED",
        name="audit_action",
    )
    new_audit_action_enum.create(bind, checkfirst=False)

    op.execute(
        "ALTER TABLE audit_logs "
        "ALTER COLUMN action TYPE audit_action "
        "USING action::text::audit_action"
    )

    op.execute("DROP TYPE audit_action_old")
