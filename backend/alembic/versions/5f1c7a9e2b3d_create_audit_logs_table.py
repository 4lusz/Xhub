"""create audit logs table

Etapa 5 - Auditoria Administrativa. Cria a tabela `audit_logs`, append-only
por regra de negocio (garantida na camada de repository, nao no banco --
nenhuma trigger/regra de banco impede update/delete aqui de proposito,
para manter a migration simples; a garantia fica em
`AuditLogRepository`).

Revision ID: 5f1c7a9e2b3d
Revises: 3a0a95ca8976
Create Date: 2026-07-07 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5f1c7a9e2b3d"
down_revision: Union[str, None] = "3a0a95ca8976"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

audit_action_enum = postgresql.ENUM(
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


def upgrade() -> None:
    bind = op.get_bind()
    audit_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "action",
            postgresql.ENUM(
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
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"]
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_target_id"), "audit_logs", ["target_id"])
    op.create_index(
        op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    bind = op.get_bind()
    audit_action_enum.drop(bind, checkfirst=True)
