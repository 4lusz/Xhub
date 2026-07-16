"""add rendered_text to post_accounts

Funcionalidade Publicacao Inteligente (ver
docs/ROADMAP_PUBLICACAO_INTELIGENTE.md). `PostAccount.rendered_text`
guarda o texto efetivamente publicado em cada conta quando houver
variacao gerada por IA ou edicao manual, preservando `Post.text` sempre
como o texto original escrito pelo usuario.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "post_accounts",
        sa.Column("rendered_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("post_accounts", "rendered_text")
