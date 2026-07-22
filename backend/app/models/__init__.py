"""
Agrega todos os models de dominio num unico ponto de import.

Isso garante que `Base.metadata` fique completo (usado pelo Alembic
autogenerate) e permite `from app.models import User, Post, ...` no
resto da aplicacao.
"""

from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.models.audit_log import AuditLog
from app.models.enums import (
    AuditAction,
    MediaType,
    PostAccountStatus,
    PostStatus,
    SubscriptionStatus,
    UserRole,
)
from app.models.jitter_settings import JitterSettings
from app.models.oauth_session import OAuthSession
from app.models.plan import Plan
from app.models.post import Post
from app.models.post_account import PostAccount
from app.models.post_media import PostMedia
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.refresh_token import RefreshToken
from app.models.scheduled_post import ScheduledPost
from app.models.subscription import Subscription
from app.models.twitter_account import TwitterAccount
from app.models.user import User

__all__ = [
    "User",
    "TwitterAccount",
    "Plan",
    "Subscription",
    "Post",
    "PostAccount",
    "PostMedia",
    "ScheduledPost",
    "AuditLog",
    "OAuthSession",
    "RefreshToken",
    "JitterSettings",
    "AccountMetricSnapshot",
    "PostMetricSnapshot",
    "PostStatus",
    "PostAccountStatus",
    "SubscriptionStatus",
    "UserRole",
    "AuditAction",
    "MediaType",
]
