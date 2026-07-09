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
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)
from app.database.session import get_db
from app.models.enums import PostStatus
from app.models.post import Post
from app.models.scheduled_post import ScheduledPost
from app.models.user import User
from app.services.post_service import PostService
from app.services.scheduled_post_service import ScheduledPostService

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)


class CreatePostRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=280,
    )
    twitter_account_ids: list[uuid.UUID] = Field(
        min_length=1,
    )


class PostResponse(BaseModel):
    id: str
    user_id: str
    text: str
    status: PostStatus
    created_at: datetime
    updated_at: datetime


class SchedulePostRequest(BaseModel):
    scheduled_for: datetime


class ScheduledPostResponse(BaseModel):
    id: str
    post_id: str
    scheduled_for: datetime
    executed: bool
    attempts: int
    last_error: str | None


def _to_post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        user_id=str(post.user_id),
        text=post.text,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
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
            text=request.text,
            twitter_account_ids=request.twitter_account_ids,
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
