"""Regras puras de metricas de desempenho (visao de Resultados).

Segue o mesmo padrao de `app.domain.content_invariants`/`policies`:
funcoes puras, sem I/O, sem SQLAlchemy, sem FastAPI. Usado por
`MetricsService` para calcular tendencia (variacao percentual entre
periodos) e anomalia de alcance (queda de desempenho de uma conta em
relacao ao seu proprio historico -- nunca comparado entre contas
diferentes, ja que o volume normal varia demais de conta para conta).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


def compute_percent_change(current: int, previous: int) -> float | None:
    """Variacao percentual de `previous` para `current` (ex.: 0.25 = alta
    de 25%; -0.62 = queda de 62%). `None` quando `previous` e zero --
    percentual indefinido, nao "infinito" nem zero."""
    if previous <= 0:
        return None
    return (current - previous) / previous


@dataclass(frozen=True)
class AnomalyResult:
    """Resultado da deteccao de queda de alcance de uma conta.

    `has_enough_data=False` significa que a conta ainda nao tem posts
    suficientes com metrica coletada para uma comparacao confiavel --
    nesse caso `is_anomalous` e sempre `False` (nunca alarma sem base).
    """

    has_enough_data: bool
    is_anomalous: bool
    baseline_average: float | None
    recent_average: float | None
    drop_ratio: float | None


def detect_reach_anomaly(
    impressions_oldest_to_newest: Sequence[int],
    *,
    recent_window: int,
    min_total_posts: int,
    drop_threshold: float,
) -> AnomalyResult:
    """Compara a media de impressoes dos `recent_window` posts mais
    recentes de uma conta contra a media dos posts anteriores (o
    "historico" dela) -- sempre a mesma conta, nunca entre contas
    diferentes (volumes de audiencia variam demais para isso fazer
    sentido). Dispara anomalia quando a queda (`drop_ratio`) e maior ou
    igual a `drop_threshold`.

    `impressions_oldest_to_newest` deve vir ordenado do post mais antigo
    para o mais recente -- a funcao usa a ORDEM para separar "recente"
    de "historico", nunca o valor em si.
    """
    total = len(impressions_oldest_to_newest)

    if total < min_total_posts or total <= recent_window:
        return AnomalyResult(
            has_enough_data=False,
            is_anomalous=False,
            baseline_average=None,
            recent_average=None,
            drop_ratio=None,
        )

    recent = impressions_oldest_to_newest[-recent_window:]
    baseline = impressions_oldest_to_newest[:-recent_window]

    baseline_average = sum(baseline) / len(baseline)
    recent_average = sum(recent) / len(recent)

    if baseline_average <= 0:
        return AnomalyResult(
            has_enough_data=True,
            is_anomalous=False,
            baseline_average=baseline_average,
            recent_average=recent_average,
            drop_ratio=None,
        )

    drop_ratio = 1 - (recent_average / baseline_average)

    return AnomalyResult(
        has_enough_data=True,
        is_anomalous=drop_ratio >= drop_threshold,
        baseline_average=baseline_average,
        recent_average=recent_average,
        drop_ratio=drop_ratio,
    )
