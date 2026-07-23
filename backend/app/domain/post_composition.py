"""Regra pura do Fluxo 2 (INDEPENDENT) de composicao de um post.

Ver `app.models.enums.PostCompositionMode`, CLAUDE.md e
docs/ROADMAP_COMPOSICAO_POST.md. So existe uma regra nova aqui: no modo
INDEPENDENT, toda conta selecionada precisa ter seu proprio texto, nao
vazio -- nunca herda de um texto base (que nem existe nesse modo,
`Post.text` fica `NULL`). O resto do fluxo (resolucao de texto/custo
por conta, invariantes, obrigatoriedade de variacao) e exclusivo do
modo SHARED e continua vivendo em `app.domain.policies`/
`app.domain.content_invariants`, sem mudanca -- nao se aplica ao modo
INDEPENDENT (nao ha "original" contra o qual comparar nem variacao
gerada por IA).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence


def find_accounts_missing_independent_text(
    twitter_account_ids: Sequence[uuid.UUID],
    rendered_texts: Mapping[uuid.UUID, str] | None,
) -> list[uuid.UUID]:
    """Contas selecionadas sem um texto proprio valido (nao vazio) --
    lista vazia significa que todas tem. Usado apenas no modo
    INDEPENDENT, onde isso e sempre obrigatorio (no modo SHARED, texto
    por conta e sempre opcional -- ver `PostService._validate_rendered_texts`)."""
    provided = rendered_texts or {}
    return [
        account_id
        for account_id in twitter_account_ids
        if not (provided.get(account_id) or "").strip()
    ]
