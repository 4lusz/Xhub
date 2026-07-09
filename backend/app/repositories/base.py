"""Repository base generico para acesso a dados com SQLAlchemy 2.0."""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Operacoes CRUD comuns para models SQLAlchemy.

    O repository nao faz commit. A transacao deve ser controlada pela
    camada chamadora (rota/service/unit of work), mantendo esta camada
    restrita ao acesso ao banco.
    """

    def __init__(self, db: Session, model: type[ModelType]) -> None:
        self.db = db
        self.model = model

    def get(self, id: uuid.UUID) -> ModelType | None:
        """Busca um registro pela chave primaria."""
        return self.db.get(self.model, id)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Lista registros paginados."""
        statement = select(self.model).offset(offset).limit(limit)
        return self.db.scalars(statement).all()

    def count(self) -> int:
        """Conta todos os registros do model."""
        statement = select(func.count()).select_from(self.model)
        return self.db.scalar(statement) or 0

    def exists(self, id: uuid.UUID) -> bool:
        """Verifica se existe um registro com a chave primaria informada."""
        return self.get(id) is not None

    def create(self, data: Mapping[str, Any]) -> ModelType:
        """Cria uma instancia, adiciona na sessao e sincroniza com o banco."""
        instance = self.model(**data)
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def update(self, instance: ModelType, data: Mapping[str, Any]) -> ModelType:
        """Atualiza campos de uma instancia existente."""
        for field, value in data.items():
            setattr(instance, field, value)

        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelType) -> None:
        """Remove uma instancia existente."""
        self.db.delete(instance)
        self.db.flush()

    def delete_by_id(self, id: uuid.UUID) -> bool:
        """Remove um registro pela chave primaria quando ele existir."""
        instance = self.get(id)
        if instance is None:
            return False

        self.delete(instance)
        return True
