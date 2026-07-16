"""Model PostMedia -- imagem/gif/video anexado a um Post.

A midia e parte da publicacao, nao uma entidade independente: pertence
sempre a um unico `Post` e e publicada de forma IDENTICA em todas as
contas de destino desse post (apenas o texto varia por conta via
`PostAccount.rendered_text` -- ver Publicacao Inteligente). A IA nunca
toca em midia.

`post_id` e nullable porque o arquivo e enviado (`POST /media/upload`)
e armazenado ANTES do post existir, seguindo o mesmo fluxo do
compositor do X: o usuario anexa midia enquanto ainda escreve o texto,
com preview imediato, e so entao confirma a criacao do post
(`POST /posts`, que anexa a midia ja enviada via `media_ids`). Uma
midia com `post_id=NULL` pertence apenas ao usuario que fez o upload
(`user_id`) e ainda nao foi confirmada em nenhum post.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import MediaType

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class PostMedia(TimestampMixin, Base):
    __tablename__ = "post_media"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    media_type: Mapped[MediaType] = mapped_column(
        SqlEnum(MediaType, name="media_type", native_enum=True),
        nullable=False,
    )
    # Caminho relativo a `settings.MEDIA_STORAGE_DIR` -- nunca um
    # caminho absoluto do host (ver `app.core.media_storage`).
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Ordem de exibicao/publicacao dentro do post (0..3). NULL enquanto
    # a midia ainda nao foi anexada a nenhum post.
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    post: Mapped["Post | None"] = relationship(back_populates="media")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<PostMedia id={self.id} media_type={self.media_type.value}>"
