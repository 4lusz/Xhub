"""add must_change_password to users

Primeiro acesso obrigatorio (ver docs/ROADMAP_PRIMEIRO_ACESSO.md).
Usuarios EXISTENTES sao migrados com `must_change_password=False`
(preserva o comportamento atual -- ninguem e forcado retroativamente a
trocar de senha so por causa desta migration); a partir de agora, todo
usuario NOVO nasce com `must_change_password=True` por padrao no model
(`app.models.user.User`), aplicado pelo ORM em cada INSERT -- por isso
o `server_default` e removido logo em seguida, para nao mascarar um
INSERT feito fora do ORM que esqueca de definir o campo.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-17 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
