"""Enums de dominio do XHub."""

import enum


class UserRole(str, enum.Enum):
    """Papeis de usuario, na camada de dominio (independente de ORM).

    Nota (auditoria item 16): existe um `UserRole` equivalente em
    `app.models.enums` (enum nativo do Postgres usado pela coluna
    `users.role`). Os dois sao reconciliados manualmente em
    `app.auth.dependencies._to_user_context`
    (`DomainUserRole(user.role.value)`). Nao ha bug hoje -- os valores
    sao identicos -- mas os dois enums precisam ser mantidos em sincronia
    manualmente caso um novo papel seja adicionado no futuro. Mantido
    como estava (a unificacao dos dois enums em um so exigiria alterar a
    modelagem SQLAlchemy existente, fora do escopo desta correcao)."""

    CLIENT = "client"
    ADMIN = "admin"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"
