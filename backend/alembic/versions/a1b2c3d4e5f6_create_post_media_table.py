"""create post_media table

Suporte a midia (imagem/gif/video) na publicacao (ver
docs/ROADMAP_MEDIA.md). `PostMedia.post_id` e nullable porque o
arquivo e enviado e armazenado ANTES do post existir (fluxo tipo
compositor do X: upload com preview imediato, post confirmado depois
via `POST /posts` com `media_ids`).

Revision ID: a1b2c3d4e5f6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

media_type_enum = postgresql.ENUM(
    "IMAGE", "GIF", "VIDEO",
    name="media_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    media_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "post_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "media_type",
            postgresql.ENUM("IMAGE", "GIF", "VIDEO", name="media_type", create_type=False),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_media_post_id"), "post_media", ["post_id"])
    op.create_index(op.f("ix_post_media_user_id"), "post_media", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_post_media_user_id"), table_name="post_media")
    op.drop_index(op.f("ix_post_media_post_id"), table_name="post_media")
    op.drop_table("post_media")

    bind = op.get_bind()
    media_type_enum.drop(bind, checkfirst=True)
