"""create revoked_access_tokens table

Auditoria de seguranca completa pedida pelo usuario antes de um commit
(item 4 do checklist -- JWT): access tokens eram stateless por design
(nunca invalidados no logout, so expiravam naturalmente ate 30 min
depois). Esta tabela e uma denylist minima: guarda apenas o `jti`
(claim nova em todo access token, ver `app.auth.jwt.create_access_token`)
dos tokens revogados explicitamente (logout), com `expires_at` copiado
da propria claim `exp` do token -- usado so para limpar linhas cujo
token ja expiraria de qualquer forma (ver
`RevokedAccessTokenRepository.delete_expired`, chamado a cada nova
revogacao, mantendo a tabela pequena sem precisar de um job dedicado).

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revoked_access_tokens",
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(
        op.f("ix_revoked_access_tokens_expires_at"),
        "revoked_access_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_revoked_access_tokens_expires_at"),
        table_name="revoked_access_tokens",
    )
    op.drop_table("revoked_access_tokens")
