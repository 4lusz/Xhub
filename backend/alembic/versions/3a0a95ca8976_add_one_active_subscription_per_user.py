"""add one active subscription per user constraint

Correcao arquitetural: resolve a ambiguidade entre "assinatura unica" e
"historico de assinaturas". Subscription passa a ser tratada oficialmente
como tabela de historico (append-only), e este indice unico parcial
garante, no nivel de banco, que nenhum usuario tenha mais de uma
assinatura com status=ACTIVE ao mesmo tempo -- independente de quantas
linhas com outros status existam no historico.

Nao altera nenhuma coluna, regra de negocio ou comportamento de service
ja existente.

Revision ID: 3a0a95ca8976
Revises: a3e2d9f4b6c8
Create Date: 2026-07-07 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a0a95ca8976"
down_revision: Union[str, None] = "a3e2d9f4b6c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_subscriptions_one_active_per_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_subscriptions_one_active_per_user",
        table_name="subscriptions",
    )
