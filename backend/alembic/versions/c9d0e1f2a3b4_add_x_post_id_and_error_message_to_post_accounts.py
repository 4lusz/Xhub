"""add x_post_id and error_message to post_accounts

Correcao critica (mesma classe de bug das migrations b4c5d6e7f8a9 e
9b2f6a1d7e4c): `app.models.post_account.PostAccount` sempre teve os
campos `x_post_id` (id do tweet publicado, retornado pela API do X) e
`error_message` (motivo da falha por conta) desde que o status
PUBLISHED/FAILED foi introduzido, mas a migration original
(425b5fb53a66_create_domain_models) criou a tabela `post_accounts` sem
essas duas colunas, e nenhuma migration posterior as adicionou --
f3a4b5c6d7e8 adicionou apenas `rendered_text`.

Sem esta migration, `POST /posts` falha com 500
(`psycopg.errors.UndefinedColumn: column "x_post_id" of relation
"post_accounts" does not exist`) em toda tentativa de criar um post,
porque `PostService.create_post` grava um `PostAccount` por conta
selecionada e o INSERT gerado pelo SQLAlchemy inclui todas as colunas
mapeadas no model, inclusive as duas que nunca existiram na tabela real.

Revision ID: c9d0e1f2a3b4
Revises: b4c5d6e7f8a9
Create Date: 2026-07-16 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "post_accounts",
        sa.Column("x_post_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "post_accounts",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("post_accounts", "error_message")
    op.drop_column("post_accounts", "x_post_id")
