"""add post composition_mode and per-account media

Separacao Fluxo 1 (SHARED, texto compartilhado + Publicacao Inteligente
opcional -- comportamento existente, inalterado) / Fluxo 2 (INDEPENDENT,
um tweet totalmente proprio por conta, sem texto principal, sem
Publicacao Inteligente). Ver CLAUDE.md e docs/ROADMAP_COMPOSICAO_POST.md.

- `posts.composition_mode`: enum nativo, NOT NULL, default 'SHARED' --
  todo post existente vira SHARED (comportamento identico ao anterior).
- `posts.text`: passa a ser nullable -- so e obrigatorio no modo SHARED;
  no modo INDEPENDENT nao existe texto principal (cada conta tem o seu
  proprio, em `post_accounts.rendered_text`, que ja existia e ja era
  nullable).
- `post_media.post_account_id`: FK nullable para `post_accounts.id`.
  `NULL` = midia compartilhada entre todas as contas do post
  (comportamento identico ao anterior -- Fluxo 1 nunca preenche este
  campo); preenchido = midia exclusiva daquela conta (so possivel no
  Fluxo 2, quando o usuario opta por NAO compartilhar midia).

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

composition_mode_enum = postgresql.ENUM(
    "SHARED", "INDEPENDENT",
    name="post_composition_mode",
)


def upgrade() -> None:
    bind = op.get_bind()
    composition_mode_enum.create(bind, checkfirst=True)

    op.add_column(
        "posts",
        sa.Column(
            "composition_mode",
            postgresql.ENUM("SHARED", "INDEPENDENT", name="post_composition_mode", create_type=False),
            nullable=False,
            server_default="SHARED",
        ),
    )
    # server_default so existe para preencher as linhas ja existentes
    # sem exigir um valor explicito em todo INSERT futuro -- removido
    # logo em seguida, ja que `app.models.post.Post` sempre informa o
    # valor no create() (mesmo padrao ja usado por `PostStatus`).
    op.alter_column("posts", "composition_mode", server_default=None)

    op.alter_column("posts", "text", existing_type=sa.Text(), nullable=True)

    op.add_column(
        "post_media",
        sa.Column("post_account_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_post_media_post_account_id",
        "post_media",
        "post_accounts",
        ["post_account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_post_media_post_account_id"), "post_media", ["post_account_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_post_media_post_account_id"), table_name="post_media")
    op.drop_constraint("fk_post_media_post_account_id", "post_media", type_="foreignkey")
    op.drop_column("post_media", "post_account_id")

    op.alter_column("posts", "text", existing_type=sa.Text(), nullable=False)

    op.drop_column("posts", "composition_mode")

    bind = op.get_bind()
    composition_mode_enum.drop(bind, checkfirst=True)
