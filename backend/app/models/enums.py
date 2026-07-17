"""Enums compartilhados pelos models de dominio."""

import enum


class PostStatus(str, enum.Enum):
    """Status geral de um Post (agregado de todas as contas de destino)."""

    DRAFT = "draft"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class PostAccountStatus(str, enum.Enum):
    """Status da publicacao de um Post em uma TwitterAccount especifica."""

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class SubscriptionStatus(str, enum.Enum):
    """Status de uma assinatura no XHub."""

    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class UserRole(str, enum.Enum):
    """Papeis de usuario do XHub (enum nativo do Postgres, coluna
    `users.role`).

    Nota (auditoria item 16): ha um `UserRole` equivalente em
    `app.domain.enums`, usado pela camada de dominio/politicas
    (`app.domain.policies`). Ver o comentario la para detalhes da
    reconciliacao manual entre os dois."""

    CLIENT = "client"
    ADMIN = "admin"


class AuditAction(str, enum.Enum):
    """Acoes administrativas registradas no log de auditoria.

    Cobre apenas acoes ja existentes na aplicacao (regras comerciais e
    bloqueio de usuario/assinatura). Novas acoes (posts, publicacao,
    agendamento, etc.) serao adicionadas quando essas etapas existirem --
    o valor OTHER cobre qualquer acao futura antes disso, sem exigir
    alteracao imediata do enum.
    """

    USER_BLOCKED = "user_blocked"
    USER_UNBLOCKED = "user_unblocked"
    USER_ROLE_CHANGED = "user_role_changed"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_BLOCKED = "subscription_blocked"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    EXTRA_POSTS_ADDED = "extra_posts_added"
    EXTRA_POSTS_REMOVED = "extra_posts_removed"
    PLAN_SYNCED = "plan_synced"
    TWITTER_ACCOUNT_CONNECTED = "twitter_account_connected"
    TWITTER_ACCOUNT_DISCONNECTED = "twitter_account_disconnected"
    OTHER = "other"
    USER_CREATED = "user_created"
    PLAN_UPDATED = "plan_updated"
    USER_PASSWORD_RESET = "user_password_reset"
    JITTER_SETTINGS_UPDATED = "jitter_settings_updated"


class MediaType(str, enum.Enum):
    """Categoria de midia anexada a um Post (ver
    `app.domain.media_rules` e `app.models.post_media.PostMedia`)."""

    IMAGE = "image"
    GIF = "gif"
    VIDEO = "video"
