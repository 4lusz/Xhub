"""Schemas Pydantic da tela de Resultados (metricas de desempenho).

Ver docs/ROADMAP_METRICAS.md.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AccountPortfolioSummaryResponse(BaseModel):
    twitter_account_id: str
    username: str
    display_name: str
    profile_image_url: str | None
    followers_count: int | None
    # Variacao percentual vs. o mesmo numero de dias anterior ao periodo
    # (ex.: -0.62 = caiu 62%). `None` quando nao ha dado suficiente do
    # periodo anterior para comparar.
    followers_trend: float | None
    impressions: int
    likes: int
    replies: int
    reposts: int
    impressions_trend: float | None
    # `True` somente quando ha historico suficiente E o alcance recente
    # caiu significativamente vs. o historico da PROPRIA conta (nunca
    # comparado com outras contas).
    has_anomaly: bool
    has_enough_data: bool


class AccountMetricPointResponse(BaseModel):
    collected_at: datetime
    followers_count: int | None


class AccountPostSummaryResponse(BaseModel):
    post_account_id: str
    post_id: str
    text_preview: str
    published_at: datetime
    impression_count: int | None
    like_count: int | None
    reply_count: int | None
    repost_count: int | None


class AccountMetricsDetailResponse(BaseModel):
    twitter_account_id: str
    username: str
    display_name: str
    followers_history: list[AccountMetricPointResponse]
    top_posts: list[AccountPostSummaryResponse]


class PostMetricPointResponse(BaseModel):
    collected_at: datetime
    impression_count: int | None
    like_count: int | None
    reply_count: int | None
    repost_count: int | None


class PostAccountMetricsDetailResponse(BaseModel):
    post_account_id: str
    twitter_account_id: str
    username: str
    published_at: datetime
    history: list[PostMetricPointResponse]
