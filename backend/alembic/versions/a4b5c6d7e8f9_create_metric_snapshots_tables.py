"""create metric snapshots tables

Serie historica de metricas de desempenho (visao "Resultados") -- ver
docs/ROADMAP_METRICAS.md. Duas tabelas, ambas append-only (nenhuma linha
e atualizada ou apagada apos criada, ver
`AccountMetricSnapshotRepository`/`PostMetricSnapshotRepository`):

- `account_metric_snapshots`: seguidores da conta ao longo do tempo.
- `post_metric_snapshots`: impressoes/curtidas/respostas/republicacoes/
  citacoes de um tweet publicado, coletadas periodicamente enquanto o
  post estiver dentro da janela de retencao configurada.

Revision ID: a4b5c6d7e8f9
Revises: f6a7b8c9d0e1
Create Date: 2026-07-17 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_metric_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("twitter_account_id", sa.Uuid(), nullable=False),
        sa.Column("followers_count", sa.Integer(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["twitter_account_id"], ["twitter_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_metric_snapshots_twitter_account_id",
        "account_metric_snapshots",
        ["twitter_account_id"],
    )
    op.create_index(
        "ix_account_metric_snapshots_collected_at",
        "account_metric_snapshots",
        ["collected_at"],
    )

    op.create_table(
        "post_metric_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_account_id", sa.Uuid(), nullable=False),
        sa.Column("twitter_account_id", sa.Uuid(), nullable=False),
        sa.Column("impression_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("reply_count", sa.Integer(), nullable=True),
        sa.Column("repost_count", sa.Integer(), nullable=True),
        sa.Column("quote_count", sa.Integer(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_account_id"], ["post_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["twitter_account_id"], ["twitter_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_post_metric_snapshots_post_account_id",
        "post_metric_snapshots",
        ["post_account_id"],
    )
    op.create_index(
        "ix_post_metric_snapshots_twitter_account_id",
        "post_metric_snapshots",
        ["twitter_account_id"],
    )
    op.create_index(
        "ix_post_metric_snapshots_collected_at",
        "post_metric_snapshots",
        ["collected_at"],
    )


def downgrade() -> None:
    op.drop_table("post_metric_snapshots")
    op.drop_table("account_metric_snapshots")
