"""Rotas de metricas de desempenho (tela "Resultados").

Ver docs/ROADMAP_METRICAS.md. Somente leitura -- a coleta em si acontece
no worker do scheduler (`app.scheduler`), nunca em resposta a uma
requisicao HTTP. Toda consulta e escopada ao usuario autenticado (posse
verificada em `MetricsService`, mesmo padrao de IDOR do resto da
aplicacao).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user, get_metrics_service
from app.core.exceptions import BaseAppException, NotFoundException
from app.models.user import User
from app.schemas.metrics import (
    AccountMetricsDetailResponse,
    AccountPortfolioSummaryResponse,
    PostAccountMetricsDetailResponse,
)
from app.services.metrics_service import (
    AccountMetricsDetail,
    AccountPortfolioSummary,
    MetricsService,
    PostAccountMetricsDetail,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _raise_http_error(exc: BaseAppException) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND

    raise HTTPException(status_code=status_code, detail=exc.message) from exc


def _to_portfolio_response(summary: AccountPortfolioSummary) -> AccountPortfolioSummaryResponse:
    return AccountPortfolioSummaryResponse(
        twitter_account_id=str(summary.twitter_account_id),
        username=summary.username,
        display_name=summary.display_name,
        profile_image_url=summary.profile_image_url,
        followers_count=summary.followers_count,
        followers_trend=summary.followers_trend,
        impressions=summary.impressions,
        likes=summary.likes,
        replies=summary.replies,
        reposts=summary.reposts,
        impressions_trend=summary.impressions_trend,
        has_anomaly=summary.has_anomaly,
        has_enough_data=summary.has_enough_data,
    )


def _to_account_detail_response(detail: AccountMetricsDetail) -> AccountMetricsDetailResponse:
    return AccountMetricsDetailResponse(
        twitter_account_id=str(detail.twitter_account_id),
        username=detail.username,
        display_name=detail.display_name,
        followers_history=[
            {"collected_at": point.collected_at, "followers_count": point.followers_count}
            for point in detail.followers_history
        ],
        top_posts=[
            {
                "post_account_id": str(post.post_account_id),
                "post_id": str(post.post_id),
                "text_preview": post.text_preview,
                "published_at": post.published_at,
                "impression_count": post.impression_count,
                "like_count": post.like_count,
                "reply_count": post.reply_count,
                "repost_count": post.repost_count,
            }
            for post in detail.top_posts
        ],
    )


def _to_post_account_detail_response(
    detail: PostAccountMetricsDetail,
) -> PostAccountMetricsDetailResponse:
    return PostAccountMetricsDetailResponse(
        post_account_id=str(detail.post_account_id),
        twitter_account_id=str(detail.twitter_account_id),
        username=detail.username,
        published_at=detail.published_at,
        history=[
            {
                "collected_at": point.collected_at,
                "impression_count": point.impression_count,
                "like_count": point.like_count,
                "reply_count": point.reply_count,
                "repost_count": point.repost_count,
            }
            for point in detail.history
        ],
    )


@router.get("/accounts", response_model=list[AccountPortfolioSummaryResponse])
def get_portfolio_summary(
    period_days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> list[AccountPortfolioSummaryResponse]:
    summaries = metrics_service.get_portfolio_summary(current_user.id, period_days=period_days)
    return [_to_portfolio_response(summary) for summary in summaries]


@router.get("/accounts/{account_id}", response_model=AccountMetricsDetailResponse)
def get_account_metrics_detail(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> AccountMetricsDetailResponse:
    try:
        detail = metrics_service.get_account_detail(current_user.id, account_id)
    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_account_detail_response(detail)


@router.get("/post-accounts/{post_account_id}", response_model=PostAccountMetricsDetailResponse)
def get_post_account_metrics_detail(
    post_account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> PostAccountMetricsDetailResponse:
    try:
        detail = metrics_service.get_post_account_detail(current_user.id, post_account_id)
    except BaseAppException as exc:
        _raise_http_error(exc)

    return _to_post_account_detail_response(detail)
