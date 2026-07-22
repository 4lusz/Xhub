"""add security question to users

Segundo fator simples de login para administradores (ver
docs/AUDITORIA_SEGURANCA.md, auditoria pos-deploy 2026-07-22): pergunta
de seguranca com resposta hasheada (mesmo esquema bcrypt de
`password_hash`, nunca texto puro). Ambas colunas nullable -- opcional
por admin (quem configurar, passa a exigir a resposta no login; quem
nao configurar, login continua normal, sem segundo fator).

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-07-22 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("security_question", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "users", sa.Column("security_answer_hash", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "security_answer_hash")
    op.drop_column("users", "security_question")
