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
