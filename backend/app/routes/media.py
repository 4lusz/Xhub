"""Rotas de midia (imagem/gif/video) anexada a posts.

Ver docs/ROADMAP_MEDIA.md. Fluxo tipo compositor do X: o arquivo e
enviado e validado ANTES do post existir (`POST /media/upload`), com
preview imediato (`GET /media/{id}/file`); a confirmacao do post
(`POST /posts`, ver app.routes.post) anexa a midia ja enviada via
`media_ids`.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.dependencies import get_current_user, get_media_service
from app.core import media_storage
from app.core.exceptions import BaseAppException, NotFoundException, ValidationException
from app.database.session import get_db
from app.models.post_media import PostMedia
from app.models.user import User
from app.schemas.media import PostMediaResponse
from app.services.media_service import MediaService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/media", tags=["media"])


def _to_media_response(media: PostMedia) -> PostMediaResponse:
    return PostMediaResponse(
        id=str(media.id),
        media_type=media.media_type.value,
        content_type=media.content_type,
        file_size_bytes=media.file_size_bytes,
        position=media.position,
        created_at=media.created_at,
        post_account_id=None,
    )


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    raise HTTPException(status_code=status_code, detail=exc.message) from exc


@router.post(
    "/upload",
    response_model=PostMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_media(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> PostMediaResponse:
    try:
        media = media_service.upload_media(user_id=current_user.id, upload_file=file)
        db.commit()
        db.refresh(media)
        return _to_media_response(media)
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)


@router.get("/{media_id}/file")
def download_media_file(
    media_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> FileResponse:
    try:
        media = media_service.get_owned_media(media_id, current_user.id)
    except BaseAppException as exc:
        _raise_http_error(exc)

    absolute_path = media_storage.resolve_path(media.storage_path)
    if not absolute_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo de midia nao encontrado.",
        )

    return FileResponse(absolute_path, media_type=media.content_type)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> None:
    try:
        media_service.delete_unattached_media(media_id, current_user.id)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)
