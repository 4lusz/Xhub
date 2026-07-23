"""Schemas Pydantic de midia (imagem/gif/video) anexada a posts.

Ver docs/ROADMAP_MEDIA.md.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PostMediaResponse(BaseModel):
    id: str
    media_type: str
    content_type: str
    file_size_bytes: int
    position: int | None
    created_at: datetime
    # `None` = midia compartilhada entre todas as contas do post; caso
    # contrario, exclusiva desta conta (so possivel no modo INDEPENDENT
    # -- ver app.models.enums.PostCompositionMode).
    post_account_id: str | None = None
