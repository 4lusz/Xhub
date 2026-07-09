"""
Agrega todos os models de dominio num unico ponto de import.

Isso garante que `Base.metadata` fique completo (usado pelo Alembic
autogenerate) e permite `from app.models import User, Post, ...` no
resto da aplicacao.
"""

from app.models.audit_log import AuditLog
from app.models.enums import (
    AuditAction,
    PostAccountStatus,
    PostStatus,
    SubscriptionStatus,
    UserRole,
)
from app.models.oauth_session import OAuthSession
from app.models.plan import Plan
from app.models.post import Post
from app.models.post_account import PostAccount
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
    "ScheduledPost",
    "AuditLog",
    "OAuthSession",
    "RefreshToken",
    "PostStatus",
    "PostAccountStatus",
    "SubscriptionStatus",
    "UserRole",
    "AuditAction",
]
