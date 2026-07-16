"""Model PostAccount -- resultado da publicacao de um Post numa TwitterAccount."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import PostAccountStatus

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.twitter_account import TwitterAccount


class PostAccount(TimestampMixin, Base):
    """Uma linha por (Post, TwitterAccount) -- o "fan-out" da publicacao."""

    __tablename__ = "post_accounts"
    __table_args__ = (
        UniqueConstraint("post_id", "twitter_account_id", name="uq_post_twitter_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    twitter_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("twitter_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[PostAccountStatus] = mapped_column(
        SqlEnum(PostAccountStatus, name="post_account_status", native_enum=True),
        nullable=False,
        default=PostAccountStatus.PENDING,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    x_post_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Publicacao Inteligente (ver docs/ROADMAP_PUBLICACAO_INTELIGENTE.md):
    # texto efetivamente publicado NESTA conta quando houver variacao
    # gerada por IA ou edicao manual. `Post.text` continua sendo sempre
    # o texto original escrito pelo usuario e nunca e sobrescrito.
    # `NULL` para posts criados antes desta funcionalidade, ou quando a
    # regra de negocio permite publicar o texto original (1 conta, ou
    # 2-4 contas sem variacao aplicada) -- nesses casos,
    # `PostService.publish_post` usa `rendered_text or post.text`.
    rendered_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    post: Mapped["Post"] = relationship(back_populates="post_accounts")
    twitter_account: Mapped["TwitterAccount"] = relationship(back_populates="post_accounts")

    def __repr__(self) -> str:
        return f"<PostAccount id={self.id} status={self.status.value}>"
