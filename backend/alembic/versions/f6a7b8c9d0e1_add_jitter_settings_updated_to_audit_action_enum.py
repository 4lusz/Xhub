"""add JITTER_SETTINGS_UPDATED value to audit_action enum

Jitter (ver docs/ROADMAP_JITTER.md): `PATCH /admin/jitter-settings`
registra `AuditAction.JITTER_SETTINGS_UPDATED` na mesma transacao da
atualizacao -- mesma classe de correcao preventiva das migrations
9b2f6a1d7e4c, b4c5d6e7f8a9 e d4e5f6a7b8c9 (adicionar o valor ao enum
nativo do Postgres ANTES do primeiro uso, evitando o 500 "invalid
input value for enum audit_action").

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-17 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'JITTER_SETTINGS_UPDATED'")


def downgrade() -> None:
    bind = op.get_bind()

    in_use = bind.execute(
        sa.text("SELECT COUNT(*) FROM audit_logs WHERE action = 'JITTER_SETTINGS_UPDATED'")
    ).scalar_one()

    if in_use:
        raise RuntimeError(
            "Downgrade abortado: existem "
            f"{in_use} audit_logs com action JITTER_SETTINGS_UPDATED. "
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
        "USER_PASSWORD_RESET",
        name="audit_action",
    )
    new_audit_action_enum.create(bind, checkfirst=False)

    op.execute(
        "ALTER TABLE audit_logs "
        "ALTER COLUMN action TYPE audit_action "
        "USING action::text::audit_action"
    )

    op.execute("DROP TYPE audit_action_old")
