"""add profile_image_url to twitter_accounts

Passa a persistir a URL da foto de perfil real da conta do X
(`profile_image_url` de `GET /2/users/me`), usada pelo frontend no
lugar do avatar gerado a partir das iniciais do nome. NULL para contas
conectadas antes desta migration, ate serem reconectadas.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "twitter_accounts",
        sa.Column("profile_image_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("twitter_accounts", "profile_image_url")
