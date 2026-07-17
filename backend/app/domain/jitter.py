"""Sorteio do atraso (jitter) aplicado ENTRE publicacoes em contas
diferentes de um mesmo post (ver docs/ROADMAP_JITTER.md).

Funcao pura (sem I/O, sem SQLAlchemy, sem `time.sleep`) -- segue o
mesmo padrao de `app.domain.media_rules`/`app.domain.content_invariants`.
Quem efetivamente aguarda o tempo sorteado e registra o log e
`app.services.jitter_service.JitterService`, a camada correta para
efeitos colaterais (I/O), preservando este modulo puro e facil de
testar isoladamente.
"""

from __future__ import annotations

import random


def sample_jitter_delay_seconds(min_seconds: float, max_seconds: float) -> float:
    """Amostra um atraso em segundos por distribuicao uniforme entre
    `min_seconds` e `max_seconds` (ambos inclusive). Cada chamada e
    independente -- nunca reaproveita o valor de uma amostragem
    anterior (`random.uniform` gera um novo numero a cada chamada).

    Assume que `min_seconds <= max_seconds` e `min_seconds >= 0` --
    essa invariante e garantida pela validacao de
    `JitterService.update_settings` antes de qualquer valor ser
    persistido, entao nao e reforcada aqui de novo (evita duplicar
    validacao entre camadas, ver `app.domain` -- regras puras assumem
    dados ja validos vindos da camada de service).
    """
    if max_seconds <= min_seconds:
        return min_seconds

    return random.uniform(min_seconds, max_seconds)
