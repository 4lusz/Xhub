"""add USER_CREATED and PLAN_UPDATED values to audit_action enum

Correcao critica (mesma classe de bug da migration 9b2f6a1d7e4c, que
adicionou PENDING ao enum post_status): o tipo nativo `audit_action` foi
criado (migration 5f1c7a9e2b3d) com 13 labels, mas
`app.models.enums.AuditAction` ganhou depois os membros USER_CREATED
(usado por `POST /admin/users`, ver app/routes/admin.py::create_user) e
PLAN_UPDATED (usado por `PATCH /admin/plans/{plan_id}`) sem nenhuma
migration correspondente.

Sem esta migration, toda chamada a `POST /admin/users` -- a UNICA forma
de criar uma conta no XHub, ja que nao ha auto cadastro -- falha com
500 (`sqlalchemy.exc.DataError: invalid input value for enum
audit_action: "USER_CREATED"`), porque `AuditLogService.record()` roda
na mesma transacao da criacao do usuario. `PATCH /admin/plans/{plan_id}`
falha da mesma forma com "PLAN_UPDATED".

Revision ID: b4c5d6e7f8a9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE precisa rodar fora de uma transacao
    # explicita no Postgres -- ver justificativa detalhada na migration
    # 9b2f6a1d7e4c, que resolveu o mesmo problema para post_status.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_CREATED'")
        op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'PLAN_UPDATED'")


def downgrade() -> None:
    bind = op.get_bind()

    in_use = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE action IN ('USER_CREATED', 'PLAN_UPDATED')"
        )
    ).scalar_one()

    if in_use:
        raise RuntimeError(
            "Downgrade abortado: existem "
            f"{in_use} audit_logs com action USER_CREATED/PLAN_UPDATED. "
            "audit_logs e append-only por regra de negocio -- nao remova "
            "esses registros para permitir o downgrade."
        )

    # Postgres nao suporta DROP VALUE em enum: recria o tipo sem os dois
    # valores adicionados nesta migration.
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
        name="audit_action",
    )
    new_audit_action_enum.create(bind, checkfirst=False)

    op.execute(
        "ALTER TABLE audit_logs "
        "ALTER COLUMN action TYPE audit_action "
        "USING action::text::audit_action"
    )

    op.execute("DROP TYPE audit_action_old")
