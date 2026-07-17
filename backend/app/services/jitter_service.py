"""Service do Jitter -- atraso aleatorio aplicado ENTRE publicacoes em
contas diferentes de um mesmo post (ver docs/ROADMAP_JITTER.md).

Responsabilidades:
- Ler/atualizar a configuracao (min/max segundos) persistida em banco
  (`JitterSettings`, tabela singleton -- ver
  `JitterSettingsRepository`).
- Validar limites ao atualizar (usado pela rota administrativa).
- Aplicar o atraso de fato (`time.sleep`) entre uma publicacao e a
  proxima, com o log correspondente -- unico lugar do codigo que
  efetivamente pausa a execucao por causa do Jitter.

Nunca decide QUANDO aplicar o atraso (se e a primeira conta do lote,
se ha so uma conta) -- essa decisao e do chamador
(`PostService.publish_post`), que conhece o contexto de negocio da
publicacao. Este service so sabe "quanto" (config) e "como" (sleep +
log).
"""

from __future__ import annotations

import time

from app.config.settings import settings
from app.core.logging_config import get_logger
from app.domain.jitter import sample_jitter_delay_seconds
from app.models.jitter_settings import JitterSettings
from app.repositories.jitter_settings_repository import JitterSettingsRepository
from app.services.base_service import ValidationError

logger = get_logger(__name__)


class JitterService:
    def __init__(self, jitter_settings_repository: JitterSettingsRepository) -> None:
        self.jitter_settings_repository = jitter_settings_repository

    def get_settings(self) -> JitterSettings:
        return self.jitter_settings_repository.get_or_create_default()

    def update_settings(self, *, min_seconds: float, max_seconds: float) -> JitterSettings:
        """Validacao das regras de negocio do intervalo (ver
        docs/ROADMAP_JITTER.md):
        - `min_seconds` nao pode ser negativo.
        - `max_seconds` nao pode ser menor que `min_seconds`.
        - `max_seconds` respeita o teto de seguranca
          (`settings.JITTER_MAX_ALLOWED_SECONDS`), evitando um valor
          digitado por engano que tornaria a publicacao em varias
          contas absurdamente lenta.
        """
        if min_seconds < 0:
            raise ValidationError("O tempo minimo do Jitter nao pode ser negativo.")

        if max_seconds < min_seconds:
            raise ValidationError(
                "O tempo maximo do Jitter nao pode ser menor que o tempo minimo."
            )

        if max_seconds > settings.JITTER_MAX_ALLOWED_SECONDS:
            raise ValidationError(
                "O tempo maximo do Jitter nao pode exceder "
                f"{settings.JITTER_MAX_ALLOWED_SECONDS:g} segundos."
            )

        current = self.get_settings()
        return self.jitter_settings_repository.update(
            current,
            {"min_seconds": min_seconds, "max_seconds": max_seconds},
        )

    def apply_delay(self, *, post_id, account_index: int, total_accounts: int) -> float:
        """Sorteia e efetivamente aguarda um atraso independente (nunca
        reaproveita o valor de uma chamada anterior -- ver
        `app.domain.jitter.sample_jitter_delay_seconds`) usando a
        configuracao atual. O valor exato NAO e exposto ao usuario
        final em nenhuma resposta de API -- fica apenas neste log
        estruturado, para depuracao/auditoria tecnica.

        O chamador decide QUANDO chamar este metodo (nunca antes da
        primeira conta do lote, nunca se houver so uma conta) -- ver
        `PostService.publish_post`.
        """
        current_settings = self.get_settings()
        delay_seconds = sample_jitter_delay_seconds(
            current_settings.min_seconds, current_settings.max_seconds
        )

        logger.info(
            "Jitter aplicado antes da proxima publicacao.",
            extra={
                "post_id": str(post_id),
                "account_index": account_index,
                "total_accounts": total_accounts,
                "delay_seconds": round(delay_seconds, 3),
            },
        )

        time.sleep(delay_seconds)
        return delay_seconds
