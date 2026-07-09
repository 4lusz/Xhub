"""Model Post -- conteudo escrito pelo usuario para publicar em 1+ contas do X."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import PostStatus

if TYPE_CHECKING:
    from app.models.post_account import PostAccount
    from app.models.scheduled_post import ScheduledPost
    from app.models.user import User


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PostStatus] = mapped_column(
        SqlEnum(PostStatus, name="post_status", native_enum=True),
        nullable=False,
        default=PostStatus.DRAFT,
    )

    user: Mapped["User"] = relationship(back_populates="posts")
    post_accounts: Mapped[list["PostAccount"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    scheduled_post: Mapped["ScheduledPost | None"] = relationship(
        back_populates="post", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Post id={self.id} status={self.status.value}>"
