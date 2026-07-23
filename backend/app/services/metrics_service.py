"""Service de metricas de desempenho (tela "Resultados").

Ver docs/ROADMAP_METRICAS.md. Duas responsabilidades bem separadas:

- Coleta (`collect_all`): chamada periodicamente pelo scheduler (ver
  `app.scheduler`), nunca por uma rota HTTP -- percorre toda conta do X
  conectada na plataforma (de qualquer usuario) e grava um snapshot novo
  de metricas. Falha de uma conta nunca derruba a coleta das demais
  (commit/rollback por conta).
- Consulta (`get_portfolio_summary`/`get_account_detail`/
  `get_post_account_detail`): chamada pelas rotas
  (`app.routes.metrics`), sempre escopada ao usuario autenticado --
  nunca expõe dado de conta de outro usuario.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config.settings import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.exceptions import BaseAppException
from app.core.logging_config import get_logger
from app.domain.metrics import (
    AnomalyResult,
    compute_percent_change,
    detect_reach_anomaly,
    should_collect_account_metrics,
    should_collect_post_metrics,
)
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.twitter_account import TwitterAccount
from app.oauth.oauth_client import XOAuthClient
from app.repositories.account_metric_snapshot_repository import (
    AccountMetricSnapshotRepository,
)
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_metric_snapshot_repository import PostMetricSnapshotRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.services.base_service import NotFoundError

logger = get_logger(__name__)


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


@dataclass(frozen=True)
class AccountPortfolioSummary:
    twitter_account_id: uuid.UUID
    username: str
    display_name: str
    profile_image_url: str | None
    followers_count: int | None
    followers_trend: float | None
    impressions: int
    likes: int
    replies: int
    reposts: int
    impressions_trend: float | None
    has_anomaly: bool
    has_enough_data: bool


@dataclass(frozen=True)
class AccountPostSummary:
    post_account_id: uuid.UUID
    post_id: uuid.UUID
    text_preview: str
    published_at: datetime
    impression_count: int | None
    like_count: int | None
    reply_count: int | None
    repost_count: int | None


@dataclass(frozen=True)
class AccountMetricPoint:
    collected_at: datetime
    followers_count: int | None


@dataclass(frozen=True)
class AccountMetricsDetail:
    twitter_account_id: uuid.UUID
    username: str
    display_name: str
    followers_history: tuple[AccountMetricPoint, ...]
    top_posts: tuple[AccountPostSummary, ...]


@dataclass(frozen=True)
class PostMetricPoint:
    collected_at: datetime
    impression_count: int | None
    like_count: int | None
    reply_count: int | None
    repost_count: int | None


@dataclass(frozen=True)
class PostAccountMetricsDetail:
    post_account_id: uuid.UUID
    twitter_account_id: uuid.UUID
    username: str
    published_at: datetime
    history: tuple[PostMetricPoint, ...]


@dataclass(frozen=True)
class _Totals:
    impressions: int = 0
    likes: int = 0
    replies: int = 0
    reposts: int = 0


def _latest_per_post_totals(snapshots: Sequence[PostMetricSnapshot]) -> _Totals:
    """Reduz varios snapshots (um mesmo post pode ter sido coletado
    multiplas vezes no periodo) ao ULTIMO snapshot de cada post antes de
    somar -- nunca soma o mesmo post duas vezes."""
    latest_by_post: dict[uuid.UUID, PostMetricSnapshot] = {}
    for snapshot in snapshots:
        existing = latest_by_post.get(snapshot.post_account_id)
        if existing is None or snapshot.collected_at > existing.collected_at:
            latest_by_post[snapshot.post_account_id] = snapshot

    values = latest_by_post.values()
    return _Totals(
        impressions=sum(item.impression_count or 0 for item in values),
        likes=sum(item.like_count or 0 for item in values),
        replies=sum(item.reply_count or 0 for item in values),
        reposts=sum(item.repost_count or 0 for item in values),
    )


class MetricsService:
    def __init__(
        self,
        account_metric_repository: AccountMetricSnapshotRepository,
        post_metric_repository: PostMetricSnapshotRepository,
        twitter_account_repository: TwitterAccountRepository,
        post_account_repository: PostAccountRepository,
        x_oauth_client: XOAuthClient,
    ) -> None:
        self.account_metric_repository = account_metric_repository
        self.post_metric_repository = post_metric_repository
        self.twitter_account_repository = twitter_account_repository
        self.post_account_repository = post_account_repository
        self.x_oauth_client = x_oauth_client
        self.db = account_metric_repository.db

    # ------------------------------------------------------------------ #
    # Coleta (worker do scheduler -- ver app.scheduler)
    # ------------------------------------------------------------------ #

    def collect_all(self) -> None:
        """Percorre TODAS as contas do X conectadas na plataforma (de
        qualquer usuario), em paginas, coletando um snapshot novo de
        cada uma. Uma conta com falha (token revogado, API do X fora do
        ar, etc.) nunca impede a coleta das demais -- commit/rollback
        por conta, nao por lote inteiro."""
        offset = 0
        page_size = 100

        while True:
            accounts = self.twitter_account_repository.list(offset=offset, limit=page_size)
            if not accounts:
                break

            for account in accounts:
                try:
                    self._collect_for_account(account)
                    self.db.commit()
                except Exception:  # noqa: BLE001
                    self.db.rollback()
                    logger.exception(
                        "Falha inesperada ao coletar metricas de uma conta.",
                        extra={"twitter_account_id": str(account.id)},
                    )

            if len(accounts) < page_size:
                break
            offset += page_size

    def _collect_for_account(self, twitter_account: TwitterAccount) -> None:
        try:
            access_token = self._get_valid_access_token(twitter_account)
        except BaseAppException as exc:
            logger.warning(
                "Token invalido para coleta de metricas -- conta ignorada nesta rodada.",
                extra={"twitter_account_id": str(twitter_account.id), "error": exc.message},
            )
            return

        now = datetime.now(UTC)

        if self._should_collect_account_metrics_now(twitter_account.id, now):
            try:
                account_metrics = self.x_oauth_client.get_account_metrics(access_token)
                self.account_metric_repository.create(
                    {
                        "twitter_account_id": twitter_account.id,
                        "followers_count": account_metrics.followers_count,
                    }
                )
            except BaseAppException as exc:
                logger.warning(
                    "Falha ao coletar metricas de conta.",
                    extra={"twitter_account_id": str(twitter_account.id), "error": exc.message},
                )

        since = now - timedelta(days=settings.METRICS_POST_RETENTION_DAYS)
        post_accounts = self.post_account_repository.list_published_within_by_account(
            twitter_account.id, since
        )
        latest_by_post_account = self.post_metric_repository.get_latest_by_post_accounts(
            [post_account.id for post_account in post_accounts]
        )
        by_x_post_id = {
            post_account.x_post_id: post_account
            for post_account in post_accounts
            if post_account.x_post_id
            and should_collect_post_metrics(
                published_at=post_account.published_at,
                last_collected_at=(
                    latest_by_post_account[post_account.id].collected_at
                    if post_account.id in latest_by_post_account
                    else None
                ),
                now=now,
                recent_window_hours=settings.METRICS_POST_RECENT_WINDOW_HOURS,
                recent_interval_hours=settings.METRICS_POST_RECENT_INTERVAL_HOURS,
                aging_window_days=settings.METRICS_POST_AGING_WINDOW_DAYS,
                aging_interval_hours=settings.METRICS_POST_AGING_INTERVAL_HOURS,
            )
        }
        if not by_x_post_id:
            return

        for batch in _chunked(list(by_x_post_id.keys()), 100):
            try:
                metrics_batch = self.x_oauth_client.get_tweet_metrics(access_token, batch)
            except BaseAppException as exc:
                logger.warning(
                    "Falha ao coletar metricas de posts.",
                    extra={"twitter_account_id": str(twitter_account.id), "error": exc.message},
                )
                continue

            for tweet_metrics in metrics_batch:
                post_account = by_x_post_id.get(tweet_metrics.tweet_id)
                if post_account is None:
                    continue

                self.post_metric_repository.create(
                    {
                        "post_account_id": post_account.id,
                        "twitter_account_id": twitter_account.id,
                        "impression_count": tweet_metrics.impression_count,
                        "like_count": tweet_metrics.like_count,
                        "reply_count": tweet_metrics.reply_count,
                        "repost_count": tweet_metrics.repost_count,
                        "quote_count": tweet_metrics.quote_count,
                    }
                )

    def _should_collect_account_metrics_now(
        self, twitter_account_id: uuid.UUID, now: datetime
    ) -> bool:
        last_post = self.post_account_repository.list_published_by_account(
            twitter_account_id, limit=1
        )
        last_snapshot = self.account_metric_repository.get_latest_by_account(
            twitter_account_id
        )
        return should_collect_account_metrics(
            last_post_published_at=last_post[0].published_at if last_post else None,
            last_collected_at=last_snapshot.collected_at if last_snapshot else None,
            now=now,
            inactive_after_days=settings.METRICS_ACCOUNT_INACTIVE_AFTER_DAYS,
            inactive_collection_interval_hours=(
                settings.METRICS_ACCOUNT_INACTIVE_COLLECTION_INTERVAL_HOURS
            ),
        )

    def _get_valid_access_token(self, twitter_account: TwitterAccount) -> str:
        """Mesma logica de renovacao de `PostService._get_valid_access_token`
        -- duplicada de proposito (pequena, ja validada em producao) em
        vez de acoplar `MetricsService` a `PostService` so para
        reaproveitar este trecho."""
        now = datetime.now(UTC)
        expires_at = twitter_account.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at <= now:
            tokens = self.x_oauth_client.refresh_access_token(
                refresh_token=decrypt_token(twitter_account.refresh_token),
            )
            self.twitter_account_repository.update(
                twitter_account,
                {
                    "access_token": encrypt_token(tokens.access_token),
                    "refresh_token": encrypt_token(tokens.refresh_token),
                    "expires_at": tokens.expires_at,
                },
            )
            self.db.commit()
            return tokens.access_token

        return decrypt_token(twitter_account.access_token)

    # ------------------------------------------------------------------ #
    # Consulta (rotas -- sempre escopada ao usuario autenticado)
    # ------------------------------------------------------------------ #

    def get_portfolio_summary(
        self, user_id: uuid.UUID, *, period_days: int
    ) -> list[AccountPortfolioSummary]:
        accounts = self.twitter_account_repository.list_by_user(user_id, limit=1000)
        now = datetime.now(UTC)
        period_start = now - timedelta(days=period_days)
        previous_period_start = now - timedelta(days=period_days * 2)

        return [
            self._build_portfolio_summary(account, now, period_start, previous_period_start)
            for account in accounts
        ]

    def _build_portfolio_summary(
        self,
        account: TwitterAccount,
        now: datetime,
        period_start: datetime,
        previous_period_start: datetime,
    ) -> AccountPortfolioSummary:
        latest_followers = self.account_metric_repository.get_latest_by_account(account.id)
        followers_before = self.account_metric_repository.get_closest_before(
            account.id, period_start
        )
        followers_trend = None
        if latest_followers is not None and followers_before is not None:
            followers_trend = compute_percent_change(
                latest_followers.followers_count or 0,
                followers_before.followers_count or 0,
            )

        current_snapshots = self.post_metric_repository.list_by_twitter_account_since(
            account.id, period_start
        )
        previous_snapshots = [
            snapshot
            for snapshot in self.post_metric_repository.list_by_twitter_account_since(
                account.id, previous_period_start
            )
            if snapshot.collected_at < period_start
        ]

        current_totals = _latest_per_post_totals(current_snapshots)
        previous_totals = _latest_per_post_totals(previous_snapshots)

        impressions_trend = compute_percent_change(
            current_totals.impressions, previous_totals.impressions
        )

        anomaly = self._compute_anomaly(account.id, now)

        return AccountPortfolioSummary(
            twitter_account_id=account.id,
            username=account.username,
            display_name=account.display_name,
            profile_image_url=account.profile_image_url,
            followers_count=latest_followers.followers_count if latest_followers else None,
            followers_trend=followers_trend,
            impressions=current_totals.impressions,
            likes=current_totals.likes,
            replies=current_totals.replies,
            reposts=current_totals.reposts,
            impressions_trend=impressions_trend,
            has_anomaly=anomaly.has_enough_data and anomaly.is_anomalous,
            has_enough_data=anomaly.has_enough_data,
        )

    def _compute_anomaly(self, twitter_account_id: uuid.UUID, now: datetime) -> AnomalyResult:
        """Compara o alcance dos posts mais recentes desta conta contra o
        historico DELA MESMA (nunca contra outra conta -- volumes de
        audiencia variam demais entre contas para essa comparacao fazer
        sentido). Ver `app.domain.metrics.detect_reach_anomaly`."""
        lookback_start = now - timedelta(days=settings.METRICS_ANOMALY_LOOKBACK_DAYS)
        rows = self.post_metric_repository.list_with_published_at_since(
            twitter_account_id, lookback_start
        )

        latest_by_post: dict[uuid.UUID, tuple[datetime, PostMetricSnapshot]] = {}
        for snapshot, published_at in rows:
            if published_at is None:
                continue
            existing = latest_by_post.get(snapshot.post_account_id)
            if existing is None or snapshot.collected_at > existing[1].collected_at:
                latest_by_post[snapshot.post_account_id] = (published_at, snapshot)

        ordered = sorted(latest_by_post.values(), key=lambda pair: pair[0])
        impressions_oldest_to_newest = [pair[1].impression_count or 0 for pair in ordered]

        return detect_reach_anomaly(
            impressions_oldest_to_newest,
            recent_window=settings.METRICS_ANOMALY_RECENT_WINDOW,
            min_total_posts=settings.METRICS_ANOMALY_MIN_TOTAL_POSTS,
            drop_threshold=settings.METRICS_ANOMALY_DROP_THRESHOLD,
        )

    def get_account_detail(
        self, user_id: uuid.UUID, twitter_account_id: uuid.UUID
    ) -> AccountMetricsDetail:
        account = self._ensure_owned_account(user_id, twitter_account_id)

        since = datetime.now(UTC) - timedelta(days=settings.METRICS_ANOMALY_LOOKBACK_DAYS)
        followers_history = tuple(
            AccountMetricPoint(
                collected_at=snapshot.collected_at,
                followers_count=snapshot.followers_count,
            )
            for snapshot in self.account_metric_repository.list_by_account_since(
                account.id, since
            )
        )

        post_accounts = self.post_account_repository.list_published_by_account(
            account.id, limit=50
        )
        top_posts = [
            AccountPostSummary(
                post_account_id=post_account.id,
                post_id=post_account.post_id,
                text_preview=(post_account.rendered_text or post_account.post.text)[:80],
                published_at=post_account.published_at,
                impression_count=(latest.impression_count if latest else None),
                like_count=(latest.like_count if latest else None),
                reply_count=(latest.reply_count if latest else None),
                repost_count=(latest.repost_count if latest else None),
            )
            for post_account in post_accounts
            for latest in [
                self.post_metric_repository.get_latest_by_post_account(post_account.id)
            ]
        ]
        top_posts.sort(key=lambda item: item.impression_count or -1, reverse=True)

        return AccountMetricsDetail(
            twitter_account_id=account.id,
            username=account.username,
            display_name=account.display_name,
            followers_history=followers_history,
            top_posts=tuple(top_posts),
        )

    def get_post_account_detail(
        self, user_id: uuid.UUID, post_account_id: uuid.UUID
    ) -> PostAccountMetricsDetail:
        post_account = self.post_account_repository.get(post_account_id)
        if post_account is None or post_account.post.user_id != user_id:
            raise NotFoundError("Post nao encontrado para este usuario.")

        history = tuple(
            PostMetricPoint(
                collected_at=snapshot.collected_at,
                impression_count=snapshot.impression_count,
                like_count=snapshot.like_count,
                reply_count=snapshot.reply_count,
                repost_count=snapshot.repost_count,
            )
            for snapshot in self.post_metric_repository.list_by_post_account(post_account_id)
        )

        return PostAccountMetricsDetail(
            post_account_id=post_account.id,
            twitter_account_id=post_account.twitter_account_id,
            username=post_account.twitter_account.username,
            published_at=post_account.published_at,
            history=history,
        )

    def _ensure_owned_account(
        self, user_id: uuid.UUID, twitter_account_id: uuid.UUID
    ) -> TwitterAccount:
        account = self.twitter_account_repository.get(twitter_account_id)
        if account is None or account.user_id != user_id:
            raise NotFoundError("Conta do X nao encontrada para este usuario.")
        return account
