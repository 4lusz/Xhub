"""Worker de agendamento de posts.

Correcao critica (auditoria item 3): o agendamento de posts nao existia
de fato -- havia modelagem de dados (`ScheduledPost`) e `apscheduler` no
`requirements.txt`, mas nenhum processo em background efetivamente
disparava a publicacao no horario agendado.

Este modulo usa `apscheduler.schedulers.background.BackgroundScheduler`
(ja listado nas dependencias, evitando introduzir infraestrutura nova
como RabbitMQ/Celery/Kafka) para, periodicamente
(`settings.SCHEDULER_INTERVAL_SECONDS`), verificar quais agendamentos
estao vencidos e publica-los usando o fluxo ja existente e testado de
`PostService.publish_post`.

Seguranca com multiplos processos (`--workers 2` no Uvicorn, ou
multiplas replicas do container): cada processo roda seu proprio
`BackgroundScheduler`, mas a etapa de "reivindicar" os agendamentos
vencidos usa `SELECT ... FOR UPDATE SKIP LOCKED`
(`ScheduledPostRepository.list_due_for_update_skip_locked`, acionado
via `ScheduledPostService.claim_due`), garantindo que cada agendamento
seja reivindicado e processado por, no maximo, um processo por vez --
sem depender de nenhum coordenador/lock distribuido externo.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config.settings import settings
from app.core.logging_config import get_logger
from app.database.session import SessionLocal
from app.oauth.oauth_client import XOAuthClient
from app.repositories.plan_repository import PlanRepository
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_repository import PostRepository
from app.repositories.scheduled_post_repository import ScheduledPostRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.post_service import PostService
from app.services.scheduled_post_service import ScheduledPostService
from app.services.subscription_service import SubscriptionService

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def _claim_due_post_ids() -> tuple:
    """Reivindica os agendamentos vencidos em uma transacao aberta e
    retorna os `ScheduledPost` correspondentes.

    A transacao apenas e commitada depois que o worker termina de
    processar os posts agendados, preservando o lock ate que a
    operacao externa de publicacao seja concluida.
    """
    db = SessionLocal()
    try:
        scheduled_post_service = ScheduledPostService(
            ScheduledPostRepository(db),
            PostRepository(db),
        )
        claimed_schedules = scheduled_post_service.claim_due(
            datetime.now(UTC), limit=settings.SCHEDULER_BATCH_SIZE
        )
        if not claimed_schedules:
            db.commit()
            db.close()
            return None, []
        return db, claimed_schedules
    except Exception:
        db.rollback()
        logger.exception("Falha ao reivindicar agendamentos vencidos.")
        db.close()
        return None, []


def _publish_claimed_post(post_id) -> None:
    """Publica um post ja reivindicado, usando uma sessao propria,
    isolada da etapa de reivindicacao (ver `_claim_due_post_ids`)."""
    db = SessionLocal()
    try:
        post_service = PostService(
            post_repository=PostRepository(db),
            post_account_repository=PostAccountRepository(db),
            twitter_account_repository=TwitterAccountRepository(db),
            user_repository=UserRepository(db),
            x_oauth_client=XOAuthClient(),
            subscription_service=SubscriptionService(
                SubscriptionRepository(db),
                UserRepository(db),
                PlanRepository(db),
            ),
        )
        post_service.publish_post(post_id)
        logger.info(
            "Post agendado processado pelo worker.",
            extra={"post_id": str(post_id)},
        )
    except Exception:
        logger.exception(
            "Falha inesperada ao processar post agendado.",
            extra={"post_id": str(post_id)},
        )
        db.rollback()
        try:
            scheduled_post_service = ScheduledPostService(
                ScheduledPostRepository(db),
                PostRepository(db),
            )
            scheduled_post_service.record_processing_error(
                post_id, "Falha inesperada ao processar agendamento."
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Falha ao registrar erro de processamento do agendamento.",
                extra={"post_id": str(post_id)},
            )
    finally:
        db.close()


def process_due_scheduled_posts() -> None:
    """Job executado periodicamente pelo `BackgroundScheduler`."""
    claim_db, claimed_schedules = _claim_due_post_ids()

    if not claimed_schedules:
        return

    logger.info(
        "Processando agendamentos vencidos.",
        extra={"count": len(claimed_schedules)},
    )

    try:
        for scheduled_post in claimed_schedules:
            _publish_claimed_post(scheduled_post.post_id)
            scheduled_post.executed = True
            scheduled_post.attempts += 1
        claim_db.commit()
    except Exception:
        claim_db.rollback()
        logger.exception(
            "Falha ao atualizar estado do agendamento apos processamento."
        )
    finally:
        if claim_db is not None:
            claim_db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Inicia o worker in-process. Idempotente e sem efeito se
    `settings.SCHEDULER_ENABLED` estiver desligado."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler de posts desabilitado (SCHEDULER_ENABLED=false).")
        return None

    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        process_due_scheduled_posts,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="process_due_scheduled_posts",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Scheduler de posts iniciado.",
        extra={"interval_seconds": settings.SCHEDULER_INTERVAL_SECONDS},
    )
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler de posts finalizado.")
