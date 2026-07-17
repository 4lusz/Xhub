"""create jitter_settings table

Jitter entre publicacoes em contas diferentes de um mesmo post (ver
docs/ROADMAP_JITTER.md). Tabela "singleton" -- sempre exatamente uma
linha, criada sob demanda com os valores padrao na primeira leitura
(ver `JitterSettingsRepository.get_or_create_default`), por isso esta
migration NAO insere nenhuma linha (evita duplicar a logica de
default, que ja vive em `app.config.settings`).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jitter_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("min_seconds", sa.Float(), nullable=False),
        sa.Column("max_seconds", sa.Float(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("jitter_settings")
