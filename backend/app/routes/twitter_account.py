"""Rotas para contas do X conectadas pelo usuario."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_twitter_account_service
from app.core.exceptions import BaseAppException, NotFoundException, UnauthorizedException
from app.database.session import get_db
from app.models.twitter_account import TwitterAccount
from app.models.user import User
from app.services.twitter_account_service import TwitterAccountService

router = APIRouter(prefix="/twitter-accounts", tags=["twitter-accounts"])


class TwitterAccountResponse(BaseModel):
    id: str
    user_id: str
    twitter_user_id: str
    username: str
    display_name: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


def _to_twitter_account_response(account: TwitterAccount) -> TwitterAccountResponse:
    return TwitterAccountResponse(
        id=str(account.id),
        user_id=str(account.user_id),
        twitter_user_id=account.twitter_user_id,
        username=account.username,
        display_name=account.display_name,
        expires_at=account.expires_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED

    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    raise HTTPException(status_code=status_code, detail=exc.message, headers=headers) from exc


@router.get("", response_model=list[TwitterAccountResponse])
def list_twitter_accounts(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    twitter_account_service: TwitterAccountService = Depends(get_twitter_account_service),
) -> list[TwitterAccountResponse]:
    accounts = twitter_account_service.list_user_accounts(
        current_user.id,
        offset=offset,
        limit=limit,
    )
    return [_to_twitter_account_response(account) for account in accounts]


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_twitter_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    twitter_account_service: TwitterAccountService = Depends(get_twitter_account_service),
) -> None:
    try:
        twitter_account_service.disconnect_account(current_user.id, account_id)
        db.commit()
    except BaseAppException as exc:
        db.rollback()
        _raise_http_error(exc)