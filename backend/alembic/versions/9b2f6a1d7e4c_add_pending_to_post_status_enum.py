"""add PENDING value to post_status enum

Correcao critica: o tipo nativo `post_status` foi criado (migration
425b5fb53a66) apenas com os labels DRAFT, SCHEDULED, PUBLISHING,
PUBLISHED, FAILED. Porem `app.models.enums.PostStatus` sempre teve o
membro PENDING, usado por `PostService.create_post` para o status inicial
de todo post criado. Sem esta migration, `INSERT INTO posts (status=...)`
falha em qualquer banco com
`invalid input value for enum post_status: "PENDING"`.

ALTER TYPE ... ADD VALUE nao pode ser executado dentro do bloco de
transacao padrao do Alembic (o Postgres exige que o novo valor do enum
seja "commitado" antes de poder ser usado em comandos subsequentes na
mesma sessao). Por isso a alteracao roda em um `autocommit_block`,
fora da transacao normal da migration.

Nao ha suporte nativo do Postgres para remover um valor de enum
(`DROP VALUE`), por isso o downgrade reconstroi o tipo do zero e recusa
a operacao caso existam linhas com status='PENDING' (evita apagar dados
inconsistentes silenciosamente).

Revision ID: 9b2f6a1d7e4c
Revises: 5f1c7a9e2b3d
Create Date: 2026-07-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9b2f6a1d7e4c"
down_revision: Union[str, None] = "5f1c7a9e2b3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE precisa rodar fora de uma transacao
    # explicita no Postgres (>=12 permite dentro de transacao, mas o
    # novo valor so pode ser usado apos o commit dela -- o
    # autocommit_block do Alembic resolve isso em qualquer versao
    # suportada).
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE post_status ADD VALUE IF NOT EXISTS 'PENDING' "
            "BEFORE 'SCHEDULED'"
        )


def downgrade() -> None:
    bind = op.get_bind()

    in_use = bind.execute(
        sa.text("SELECT COUNT(*) FROM posts WHERE status = 'PENDING'")
    ).scalar_one()

    if in_use:
        raise RuntimeError(
            "Downgrade abortado: existem "
            f"{in_use} posts com status='PENDING'. Migre esses registros "
            "para outro status antes de remover o valor do enum."
        )

    # Postgres nao suporta DROP VALUE em enum: recria o tipo sem PENDING.
    op.execute("ALTER TYPE post_status RENAME TO post_status_old")

    new_post_status_enum = sa.Enum(
        "DRAFT", "SCHEDULED", "PUBLISHING", "PUBLISHED", "FAILED",
        name="post_status",
    )
    new_post_status_enum.create(bind, checkfirst=False)

    op.execute(
        "ALTER TABLE posts "
        "ALTER COLUMN status TYPE post_status "
        "USING status::text::post_status"
    )

    op.execute("DROP TYPE post_status_old")
