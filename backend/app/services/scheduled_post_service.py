"""Service de agendamentos de posts.

Correcao critica (auditoria item 3): `schedule_post`/`cancel_schedule`
so continham `self.not_implemented(...)`, `list_due` nunca era chamado
por ninguem e nao havia worker algum -- o agendamento nao existia na
pratica, apesar da modelagem de dados (model + migration) ja existir.
Esta classe agora implementa o fluxo completo:

- `schedule_post`: cria o registro de agendamento e move o `Post` para
  o status `SCHEDULED`.
- `cancel_schedule`: remove o agendamento (se ainda nao foi processado)
  e devolve o `Post` para `PENDING`.
- `claim_due`: usado exclusivamente pelo worker (`app.scheduler`) para
  reivindicar, de forma segura mesmo com multiplos processos rodando
  em paralelo, os agendamentos cujo horario ja chegou -- ver
  `ScheduledPostRepository.list_due_for_update_skip_locked`.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.exceptions import ConflictException
from app.models.enums import PostStatus
from app.models.scheduled_post import ScheduledPost
from app.repositories.post_repository import PostRepository
from app.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.base_service import BaseService, NotFoundError, ValidationError

# Status de Post a partir dos quais um agendamento pode ser criado --
# um post ja publicado, publicando ou ja agendado nao pode ser
# agendado novamente sem antes ser cancelado/reprocessado.
_SCHEDULABLE_STATUSES = frozenset(
    {PostStatus.DRAFT, PostStatus.PENDING, PostStatus.FAILED}
)


class ScheduledPostService(BaseService[ScheduledPost]):
    def __init__(
        self,
        scheduled_post_repository: ScheduledPostRepository,
        post_repository: PostRepository,
    ) -> None:
        super().__init__(scheduled_post_repository)
        self.scheduled_post_repository = scheduled_post_repository
        self.post_repository = post_repository

    def get_by_post(self, post_id: uuid.UUID) -> ScheduledPost | None:
        self._ensure_post_exists(post_id)
        return self.scheduled_post_repository.get_by_post(post_id)

    def list_due(self, due_at: datetime) -> Sequence[ScheduledPost]:
        return self.scheduled_post_repository.list_due(due_at)

    def schedule_post(
        self, *, post_id: uuid.UUID, scheduled_for: datetime
    ) -> ScheduledPost:
        post = self.post_repository.get(post_id)
        if post is None:
            raise NotFoundError("Post nao encontrado.")

        if post.status not in _SCHEDULABLE_STATUSES:
            raise ConflictException(
                "Post nao pode ser agendado no status atual "
                f"({post.status.value})."
            )

        if self.scheduled_post_repository.get_by_post(post_id) is not None:
            raise ConflictException("Post ja possui um agendamento ativo.")

        normalized_scheduled_for = self._normalize_datetime(scheduled_for)
        if normalized_scheduled_for <= datetime.now(UTC):
            raise ValidationError(
                "A data/hora de agendamento deve estar no futuro."
            )

        scheduled_post = self.scheduled_post_repository.create(
            {
                "post_id": post_id,
                "scheduled_for": normalized_scheduled_for,
                "executed": False,
                "attempts": 0,
            }
        )

        self.post_repository.update(post, {"status": PostStatus.SCHEDULED})

        return scheduled_post

    def cancel_schedule(self, post_id: uuid.UUID) -> None:
        scheduled_post = self.scheduled_post_repository.get_by_post(post_id)
        if scheduled_post is None:
            raise NotFoundError("Agendamento nao encontrado para este post.")

        if scheduled_post.executed:
            raise ConflictException(
                "Agendamento ja foi processado e nao pode mais ser cancelado."
            )

        post = self.post_repository.get(post_id)

        self.scheduled_post_repository.delete(scheduled_post)

        if post is not None and post.status == PostStatus.SCHEDULED:
            self.post_repository.update(post, {"status": PostStatus.PENDING})

    def claim_due(
        self, due_at: datetime, *, limit: int = 25
    ) -> list[uuid.UUID]:
        """Reivindica (trava + marca `executed=True`) os agendamentos
        cujo horario ja chegou e retorna os `post_id` correspondentes.

        Deve ser chamado dentro de uma transacao que sera commitada
        imediatamente em seguida pelo chamador (ver `app.scheduler`),
        para liberar os locks o mais rapido possivel -- a publicacao
        efetiva (chamada externa a API do X) NAO deve acontecer com
        essas linhas ainda travadas.
        """
        due_rows = self.scheduled_post_repository.list_due_for_update_skip_locked(
            due_at, limit=limit
        )

        claimed_post_ids: list[uuid.UUID] = []
        for row in due_rows:
            self.scheduled_post_repository.update(
                row,
                {"executed": True, "attempts": row.attempts + 1},
            )
            claimed_post_ids.append(row.post_id)

        return claimed_post_ids

    def record_processing_error(self, post_id: uuid.UUID, error_message: str) -> None:
        """Registra, no proprio agendamento, um erro inesperado ocorrido
        durante o processamento pelo worker (ex.: excecao que nao veio
        de `PostService.publish_post`, como uma falha de conexao com o
        banco). Falhas esperadas por conta (`PostAccount`) ja ficam
        registradas em `PostAccount.error_message`."""
        scheduled_post = self.scheduled_post_repository.get_by_post(post_id)
        if scheduled_post is not None:
            self.scheduled_post_repository.update(
                scheduled_post,
                {"last_error": error_message[:2000]},
            )

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _ensure_post_exists(self, post_id: uuid.UUID) -> None:
        if self.post_repository.get(post_id) is None:
            raise NotFoundError("Post nao encontrado.")

