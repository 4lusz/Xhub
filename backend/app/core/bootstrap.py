"""Bootstrap de dados executado no startup da aplicacao.

Correcao critica (auditoria item 1): `PlanService.sync_official_plans()`
ja existia e ja fazia a coisa certa (upsert do catalogo oficial definido
em `app.domain.plans`, preservando o preco manualmente definido pelo
administrador em planos ja existentes -- so o preco default e usado na
criacao), mas nunca era chamado em lugar nenhum: sem startup event, sem
script, sem rota. Como `POST /admin/users` exige um `plan_id` valido
(FK para `plans`), um deploy novo nascia com a tabela `plans` vazia e
nao havia como criar o primeiro usuario sem inserir linhas manualmente
via SQL direto no banco.

Este modulo fecha essa lacuna chamando `sync_official_plans()` uma vez
no startup do FastAPI (ver `app.main`), usando uma sessao dedicada
(fora do ciclo de vida de uma requisicao HTTP). Isso garante que, em
qualquer ambiente novo, `GET/POST /admin/plans` ja funcione assim que a
aplicacao subir e as migrations forem aplicadas -- sem exigir nenhuma
intervencao manual no banco.

Para reforcar ainda mais a robustez (ex.: o catalogo oficial em
`app.domain.plans` ganhar um novo plano depois que o ambiente ja esta
no ar, sem precisar reiniciar o processo), o mesmo metodo tambem fica
disponivel sob demanda via `POST /admin/plans/sync` (ver
`app.routes.admin`).
"""

from __future__ import annotations

from app.core.logging_config import get_logger
from app.database.session import SessionLocal
from app.repositories.plan_repository import PlanRepository
from app.services.plan_service import PlanService

logger = get_logger(__name__)


def sync_official_plans() -> int:
    """Garante que todos os planos do catalogo oficial existam no banco.

    Retorna a quantidade de planos sincronizados. Nunca levanta excecao
    para nao impedir a aplicacao de subir por um problema transitorio de
    banco -- loga o erro e segue (o endpoint administrativo de
    sincronizacao continua disponivel para tentar novamente depois).
    """
    db = SessionLocal()
    try:
        plan_service = PlanService(PlanRepository(db))
        plans = plan_service.sync_official_plans()
        db.commit()
        logger.info(
            "Catalogo oficial de planos sincronizado.",
            extra={"plans_count": len(plans)},
        )
        return len(plans)
    except Exception:
        db.rollback()
        logger.exception(
            "Falha ao sincronizar o catalogo oficial de planos no "
            "startup. A aplicacao continuara subindo, mas "
            "POST /admin/users pode falhar ate que os planos existam "
            "-- use POST /admin/plans/sync para tentar novamente."
        )
        return 0
    finally:
        db.close()
