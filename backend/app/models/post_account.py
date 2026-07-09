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

    post: Mapped["Post"] = relationship(back_populates="post_accounts")
    twitter_account: Mapped["TwitterAccount"] = relationship(back_populates="post_accounts")

    def __repr__(self) -> str:
        return f"<PostAccount id={self.id} status={self.status.value}>"
