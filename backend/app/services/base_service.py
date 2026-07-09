"""Base reutilizavel para services de dominio.

Correcao arquitetural: a camada de service costumava ter sua propria
hierarquia de excecoes (ServiceError/ValidationError/NotFoundError/
FeatureNotImplementedError), separada de `app.core.exceptions`. Como as
rotas so sabem tratar `BaseAppException` (ver `_raise_http_error` em
`routes/auth.py` e `routes/oauth.py`), qualquer excecao antiga do service
vazaria como erro 500 nao tratado assim que uma rota chamasse esses
services diretamente.

Os nomes abaixo sao mantidos (nenhum service precisou mudar seus imports),
mas agora sao apenas aliases para as excecoes unicas de
`app.core.exceptions`, que ja herdam de `BaseAppException`.
"""

import uuid
from collections.abc import Sequence
from typing import Generic, Never, TypeVar

from app.core.exceptions import (
    BaseAppException,
    NotFoundException,
    NotImplementedException,
    ValidationException,
)
from app.database.base import Base
from app.repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=Base)

# Aliases historicos, agora unificados com app.core.exceptions.
ServiceError = BaseAppException
ValidationError = ValidationException
NotFoundError = NotFoundException
FeatureNotImplementedError = NotImplementedException


class BaseService(Generic[ModelType]):
    """Helpers comuns para services que orquestram repositories."""

    def __init__(self, repository: BaseRepository[ModelType]) -> None:
        self.repository = repository

    def get(self, id: uuid.UUID) -> ModelType | None:
        return self.repository.get(id)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        return self.repository.list(offset=offset, limit=limit)

    def count(self) -> int:
        return self.repository.count()

    def ensure_exists(self, id: uuid.UUID, *, message: str) -> ModelType:
        entity = self.repository.get(id)
        if entity is None:
            raise NotFoundError(message)
        return entity

    def ensure(self, condition: bool, *, message: str) -> None:
        if not condition:
            raise ValidationError(message)

    def not_implemented(self, feature: str) -> Never:
        raise FeatureNotImplementedError(f"{feature} ainda nao foi implementado.")
