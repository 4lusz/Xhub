"""Rotas de posts."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    get_post_service,
    get_scheduled_post_service,
)
from app.core.exceptions import (
    BaseAppException,
    ConflictException,
    NotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)
from app.database.session import get_db
from app.domain.media_rules import MAX_MEDIA_PER_POST
from app.domain.plans import MAX_ACCOUNTS_ACROSS_PLANS
from app.models.enums import PostAccountStatus, PostCompositionMode, PostStatus
from app.models.post import Post
from app.models.scheduled_post import ScheduledPost
from app.models.user import User
from app.schemas.media import PostMediaResponse
from app.services.post_service import PostService
from app.services.scheduled_post_service import ScheduledPostService

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)


class CreatePostRequest(BaseModel):
    # Fluxo 1 (SHARED, default) vs Fluxo 2 (INDEPENDENT) -- ver
    # app.models.enums.PostCompositionMode e CLAUDE.md. Default SHARED
    # preserva o comportamento e o contrato de API anteriores a esta
    # funcionalidade para qualquer cliente existente.
    composition_mode: PostCompositionMode = Field(default=PostCompositionMode.SHARED)
    # Obrigatorio no modo SHARED (texto original do post); deve vir
    # ausente/vazio no modo INDEPENDENT, onde nao existe texto
    # principal -- cada conta tem o seu proprio em `rendered_texts`.
    text: str | None = Field(default=None, max_length=280)
    twitter_account_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=MAX_ACCOUNTS_ACROSS_PLANS,
    )
    # Modo SHARED (Publicacao Inteligente, ver
    # docs/ROADMAP_PUBLICACAO_INTELIGENTE.md): texto final por conta,
    # aprovado apos `POST /intelligent-publication/preview` (variacao
    # gerada por IA e/ou editada manualmente) -- OPCIONAL, sem este
    # campo publica sempre o texto original em todas as contas.
    # Modo INDEPENDENT: o proprio tweet de cada conta, escrito
    # manualmente -- OBRIGATORIO para toda conta selecionada, sem
    # relacao com nenhum texto original (que nem existe nesse modo).
    rendered_texts: dict[uuid.UUID, str] | None = Field(default=None)
    # Midia compartilhada (ver docs/ROADMAP_MEDIA.md): ids de PostMedia
    # ja enviados via POST /media/upload (ainda sem post_id), na ordem
    # de publicacao. Usada em ambos os modos -- identica para todas as
    # contas, nunca alterada pela Publicacao Inteligente.
    media_ids: list[uuid.UUID] | None = Field(default=None, max_length=MAX_MEDIA_PER_POST)
    # Midia individual por conta -- so disponivel no modo INDEPENDENT,
    # e mutuamente exclusiva com `media_ids` (escolha uma ou outra).
    # Chave = twitter_account_id.
    account_media_ids: dict[uuid.UUID, list[uuid.UUID]] | None = Field(default=None)


class PostAccountResponse(BaseModel):
    twitter_account_id: str
    username: str
    status: PostAccountStatus
    # error_message NAO e exposto aqui de proposito: desde que
    # `XOAuthClient.publish_post` passou a preservar o motivo original
    # retornado pela API do X (status HTTP + corpo da resposta), esse
    # texto virou tecnico demais para o cliente final -- fica disponivel
    # apenas para o administrador, via `GET /admin/posts`
    # (`AdminPostAccountResponse`), para auditoria e suporte.
    x_post_id: str | None
    # Texto efetivo desta conta -- sempre presente no modo INDEPENDENT
    # (Fluxo 2); no modo SHARED, so quando ha variacao/edicao da
    # Publicacao Inteligente (senao `None`, e o cliente publica
    # `Post.text`).
    rendered_text: str | None


class PostResponse(BaseModel):
    id: str
    user_id: str
    composition_mode: PostCompositionMode
    # `None` somente no modo INDEPENDENT (Fluxo 2) -- nao existe texto
    # principal, cada conta tem o seu proprio em `accounts` (ver
    # PostAccountResponse -- hoje sem rendered_text exposto ao cliente
    # aqui; o texto de cada conta so e necessario na tela de criacao).
    text: str | None
    status: PostStatus
    created_at: datetime
    updated_at: datetime
    accounts: list[PostAccountResponse] = Field(default_factory=list)
    media: list[PostMediaResponse] = Field(default_factory=list)


class SchedulePostRequest(BaseModel):
    scheduled_for: datetime


class ScheduledPostResponse(BaseModel):
    id: str
    post_id: str
    scheduled_for: datetime
    executed: bool
    attempts: int
    last_error: str | None


def _to_post_account_response(post_account) -> PostAccountResponse:
    return PostAccountResponse(
        twitter_account_id=str(post_account.twitter_account_id),
        username=post_account.twitter_account.username,
        status=post_account.status,
        x_post_id=post_account.x_post_id,
        rendered_text=post_account.rendered_text,
    )


def _to_media_response(media) -> PostMediaResponse:
    return PostMediaResponse(
        id=str(media.id),
        media_type=media.media_type.value,
        content_type=media.content_type,
        file_size_bytes=media.file_size_bytes,
        position=media.position,
        created_at=media.created_at,
        post_account_id=str(media.post_account_id) if media.post_account_id else None,
    )


def _to_post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        user_id=str(post.user_id),
        composition_mode=post.composition_mode,
        text=post.text,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
        accounts=[_to_post_account_response(account) for account in post.post_accounts],
        media=[_to_media_response(media) for media in post.media],
    )


def _to_scheduled_post_response(scheduled_post: ScheduledPost) -> ScheduledPostResponse:
    return ScheduledPostResponse(
        id=str(scheduled_post.id),
        post_id=str(scheduled_post.post_id),
        scheduled_for=scheduled_post.scheduled_for,
        executed=scheduled_post.executed,
        attempts=scheduled_post.attempts,
        last_error=scheduled_post.last_error,
    )


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, ConflictException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ForbiddenException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ServiceUnavailableException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    raise HTTPException(
        status_code=status_code,
        detail=exc.message,
        headers=headers,
    ) from exc


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    request: CreatePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        post = post_service.create_post(
            user_id=current_user.id,
            composition_mode=request.composition_mode,
            text=request.text,
            twitter_account_ids=request.twitter_account_ids,
            rendered_texts=request.rendered_texts,
            media_ids=request.media_ids,
            account_media_ids=request.account_media_ids,
        )

        db.commit()
        db.refresh(post)

        return _to_post_response(post)

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)


@router.get(
    "",
    response_model=list[PostResponse],
)
def list_posts(
    status_filter: PostStatus | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
) -> list[PostResponse]:
    if status_filter is None:
        posts = post_service.list_user_posts(
            current_user.id,
            offset=offset,
            limit=limit,
        )
    else:
        posts = post_service.list_user_posts_by_status(
            current_user.id,
            status_filter,
            offset=offset,
            limit=limit,
        )

    return [_to_post_response(post) for post in posts]


@router.get(
    "/{post_id}",
    response_model=PostResponse,
)
def get_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        post = post_service.get_post(post_id)

        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        return _to_post_response(post)

    except BaseAppException as exc:
        _raise_http_error(exc)


@router.post(
    "/{post_id}/publish",
    response_model=PostResponse,
)
def publish_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
) -> PostResponse:
    try:
        post = post_service.get_post(post_id)

        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        post = post_service.publish_post(post_id)

        db.commit()
        db.refresh(post)

        return _to_post_response(post)

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)


@router.post(
    "/{post_id}/schedule",
    response_model=ScheduledPostResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_post(
    post_id: uuid.UUID,
    data: SchedulePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service),
) -> ScheduledPostResponse:
    try:
        post = post_service.get_post(post_id)

        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        scheduled_post = scheduled_post_service.schedule_post(
            post_id=post_id,
            scheduled_for=data.scheduled_for,
        )

        db.commit()
        db.refresh(scheduled_post)

        return _to_scheduled_post_response(scheduled_post)

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)


@router.get(
    "/{post_id}/schedule",
    response_model=ScheduledPostResponse,
)
def get_scheduled_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service),
) -> ScheduledPostResponse:
    try:
        post = post_service.get_post(post_id)
        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        scheduled_post = scheduled_post_service.get_by_post(post_id)
        if scheduled_post is None:
            raise NotFoundException("Agendamento nao encontrado.")

        return _to_scheduled_post_response(scheduled_post)
    except BaseAppException as exc:
        _raise_http_error(exc)


@router.delete(
    "/{post_id}/schedule",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_scheduled_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service),
) -> None:
    try:
        post = post_service.get_post(post_id)

        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        scheduled_post_service.cancel_schedule(post_id)

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service),
) -> None:
    try:
        post = post_service.get_post(post_id)

        if post.user_id != current_user.id:
            raise ForbiddenException("Voce nao possui acesso a este post.")

        post_service.delete_post(post_id)

        db.commit()

    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)
