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

import uuid
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config.settings import settings
from app.core.logging_config import get_logger
from app.database.session import SessionLocal
from app.oauth.oauth_client import XOAuthClient
from app.repositories.account_metric_snapshot_repository import (
    AccountMetricSnapshotRepository,
)
from app.repositories.jitter_settings_repository import JitterSettingsRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.post_account_repository import PostAccountRepository
from app.repositories.post_media_repository import PostMediaRepository
from app.repositories.post_metric_snapshot_repository import PostMetricSnapshotRepository
from app.repositories.post_repository import PostRepository
from app.repositories.scheduled_post_repository import ScheduledPostRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.jitter_service import JitterService
from app.services.metrics_service import MetricsService
from app.services.post_service import PostService
from app.services.scheduled_post_service import ScheduledPostService
from app.services.subscription_service import SubscriptionService

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def _claim_one_due_scheduled_post() -> uuid.UUID | None:
    """Reivindica NO MAXIMO um agendamento vencido por vez, em uma
    transacao curta: `SELECT ... FOR UPDATE SKIP LOCKED` + marcar
    `executed=True`/`attempts += 1` + commit imediato -- o lock e a
    conexao sao liberados assim que a reivindicacao termina, ANTES de
    qualquer chamada de publicacao. Retorna o `post_id` reivindicado,
    ou `None` se nao houver agendamentos vencidos.

    Correcao critica (analise de escalabilidade -- clientes com muitas
    contas conectadas, ver claude.md): a versao anterior reivindicava
    ate `SCHEDULER_BATCH_SIZE` agendamentos de uma vez so e mantinha a
    MESMA transacao/conexao aberta (com os locks `FOR UPDATE` de todas
    as linhas reivindicadas) durante a publicacao de TODOS eles, so
    commitando (e liberando os locks) no final do lote inteiro. Com o
    Jitter (ver docs/ROADMAP_JITTER.md) e clientes com dezenas/centenas
    de contas conectadas, publicar um unico post agendado pode levar
    minutos; publicar ate 25 posts assim dentro da mesma transacao
    podia manter uma conexao do Postgres presa por horas. Como o job
    roda com `max_instances=1`, nenhuma outra execucao do mesmo job
    comecava enquanto isso -- ou seja, um unico post de um unico
    cliente grande podia represar TODOS os agendamentos do sistema
    (de qualquer outro cliente) por um tempo desproporcional.

    Reivindicar (e marcar `executed`) um agendamento por vez, em uma
    transacao de milissegundos, elimina esse represamento por completo:
    o lock so existe durante a propria consulta/atualizacao, nunca
    durante a chamada externa de publicacao (que roda depois, em uma
    sessao propria e isolada -- ver `_publish_claimed_post`).

    Trade-off aceito: marcar `executed=True` ANTES de publicar (em vez
    de so no final, como antes) significa que, no caso raro de o
    processo do worker morrer exatamente entre a reivindicacao e o
    termino da publicacao deste post especifico, o agendamento nao sera
    automaticamente tentado de novo pelo scheduler (fica com
    `executed=True` mas pode ter ficado parcialmente publicado). Isso e
    aceitavel porque (a) o escopo do risco e um unico post por vez, nao
    o lote inteiro; e (b) contas que ficarem `PENDING`/`FAILED` nesse
    cenario continuam podendo ser republicadas manualmente pelo usuario
    via `POST /posts/{id}/publish` (mesmo fluxo, idempotente) -- o
    represamento sistemico do lote inteiro, que acontecia sempre (nao
    so em crash raro), era o problema real a resolver.
    """
    db = SessionLocal()
    try:
        scheduled_post_service = ScheduledPostService(
            ScheduledPostRepository(db),
            PostRepository(db),
        )
        claimed = scheduled_post_service.claim_due(datetime.now(UTC), limit=1)

        if not claimed:
            db.commit()
            return None

        scheduled_post = claimed[0]
        post_id = scheduled_post.post_id
        scheduled_post.executed = True
        scheduled_post.attempts += 1
        db.commit()
        return post_id
    except Exception:
        db.rollback()
        logger.exception("Falha ao reivindicar agendamento vencido.")
        return None
    finally:
        db.close()


def _publish_claimed_post(post_id: uuid.UUID) -> None:
    """Publica um post ja reivindicado, usando uma sessao propria,
    isolada da etapa de reivindicacao (ver
    `_claim_one_due_scheduled_post`)."""
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
            post_media_repository=PostMediaRepository(db),
            jitter_service=JitterService(JitterSettingsRepository(db)),
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
    """Job executado periodicamente pelo `BackgroundScheduler`.

    Processa ate `SCHEDULER_BATCH_SIZE` agendamentos vencidos por tick,
    reivindicando e publicando UM POR VEZ (ver
    `_claim_one_due_scheduled_post`) -- nenhuma transacao de
    reivindicacao fica aberta durante a publicacao em si, entao um post
    com muitas contas conectadas (e, portanto, com o Jitter aplicado
    varias vezes -- ver docs/ROADMAP_JITTER.md) nunca prende a fila de
    agendamentos dos demais clientes atras de si.
    """
    processed = 0

    while processed < settings.SCHEDULER_BATCH_SIZE:
        post_id = _claim_one_due_scheduled_post()
        if post_id is None:
            break

        _publish_claimed_post(post_id)
        processed += 1

    if processed:
        logger.info(
            "Agendamentos vencidos processados.",
            extra={"count": processed},
        )


def collect_account_and_post_metrics() -> None:
    """Job executado periodicamente pelo `BackgroundScheduler` -- coleta
    metricas de desempenho (seguidores, impressoes, curtidas) de toda
    conta do X conectada na plataforma (ver docs/ROADMAP_METRICAS.md).

    Reaproveita o mesmo `BackgroundScheduler` in-process do agendamento
    de posts (nunca um worker/broker novo, ver `PostService`/claude.md,
    secao de arquitetura) -- so mais um job, com seu proprio intervalo
    (`settings.METRICS_COLLECTION_INTERVAL_SECONDS`, tipicamente bem
    mais espacado que o de posts, ja que cada chamada tem custo real na
    API do X, paga por uso).
    """
    if not settings.METRICS_COLLECTION_ENABLED:
        return

    db = SessionLocal()
    try:
        metrics_service = MetricsService(
            AccountMetricSnapshotRepository(db),
            PostMetricSnapshotRepository(db),
            TwitterAccountRepository(db),
            PostAccountRepository(db),
            XOAuthClient(),
        )
        metrics_service.collect_all()
        logger.info("Coleta de metricas de contas/posts concluida.")
    except Exception:
        logger.exception("Falha inesperada na coleta de metricas.")
    finally:
        db.close()


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
    scheduler.add_job(
        collect_account_and_post_metrics,
        trigger="interval",
        seconds=settings.METRICS_COLLECTION_INTERVAL_SECONDS,
        id="collect_account_and_post_metrics",
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
