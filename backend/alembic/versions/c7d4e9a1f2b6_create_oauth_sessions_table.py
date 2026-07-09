"""create oauth_sessions table

Correcao critica: o estado do fluxo OAuth2/PKCE do X (state +
code_verifier) era mantido em um dict Python em memoria
(`XOAuthService._sessions`), que nao funciona com multiplos
workers/replicas -- o login pode ser atendido por um processo e o
callback por outro, quebrando o fluxo. Esta migration cria a tabela
`oauth_sessions` para persistir esse estado de forma compartilhada
entre todos os processos da aplicacao.

Revision ID: c7d4e9a1f2b6
Revises: 9b2f6a1d7e4c
Create Date: 2026-07-08 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7d4e9a1f2b6"
down_revision: Union[str, None] = "9b2f6a1d7e4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_verifier", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", name="uq_oauth_sessions_state"),
    )
    op.create_index(
        op.f("ix_oauth_sessions_state"), "oauth_sessions", ["state"], unique=True
    )
    op.create_index(
        op.f("ix_oauth_sessions_user_id"), "oauth_sessions", ["user_id"]
    )
    op.create_index(
        op.f("ix_oauth_sessions_expires_at"), "oauth_sessions", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_sessions_expires_at"), table_name="oauth_sessions")
    op.drop_index(op.f("ix_oauth_sessions_user_id"), table_name="oauth_sessions")
    op.drop_index(op.f("ix_oauth_sessions_state"), table_name="oauth_sessions")
    op.drop_table("oauth_sessions")
