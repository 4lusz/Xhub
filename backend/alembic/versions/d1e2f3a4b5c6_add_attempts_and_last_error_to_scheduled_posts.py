"""add attempts and last_error to scheduled_posts

Correcao critica (auditoria item 3): implementa de fato o agendamento de
posts. `ScheduledPost.executed` ja existia (indicava se o worker tentou
processar o agendamento), mas nao havia como saber, sem vasculhar logs,
quantas vezes uma tentativa foi feita nem qual foi o motivo de uma
falha inesperada (ex.: erro de rede/timeout ao chamar a API do X que
nao seja um `BaseAppException`). As colunas `attempts` e `last_error`
dao essa visibilidade diretamente no registro do agendamento, sem
necessidade de correlacionar com o log da aplicacao.

Revision ID: d1e2f3a4b5c6
Revises: c7d4e9a1f2b6
Create Date: 2026-07-08 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c7d4e9a1f2b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scheduled_posts",
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    # server_default so era necessario para preencher as linhas
    # existentes durante o ALTER TABLE; a partir daqui o valor default
    # e responsabilidade da aplicacao (ver `ScheduledPost.attempts`).
    op.alter_column("scheduled_posts", "attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("scheduled_posts", "last_error")
    op.drop_column("scheduled_posts", "attempts")
