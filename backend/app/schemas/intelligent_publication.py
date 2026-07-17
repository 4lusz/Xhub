"""Schemas Pydantic da Publicacao Inteligente.

Ver `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`. Arquivo explicitamente
previsto pelo roadmap (`backend/app/schemas/intelligent_publication.py`)
-- diferente do restante das rotas do projeto, que ainda definem seus
schemas Pydantic dentro do proprio arquivo de rota (lacuna conhecida e
documentada no roadmap, nao corrigida nesta etapa).
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.plans import MAX_ACCOUNTS_ACROSS_PLANS

Strategy = Literal["original", "optional_variation", "mandatory_variation"]


class IntelligentPublicationPreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=280)
    twitter_account_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=MAX_ACCOUNTS_ACROSS_PLANS,
    )
    # Relevante apenas para 2-4 contas: reflete o estado do botao
    # "Publicacao Inteligente" no frontend (ativado por padrao). Para 1
    # conta e ignorado (nunca gera variacao); para 5+ contas e ignorado
    # (geracao sempre obrigatoria).
    apply_variation: bool = Field(default=True)


class AccountPreviewResponse(BaseModel):
    twitter_account_id: str
    username: str
    display_name: str
    text: str
    is_variation: bool
    char_count: int
    is_duplicate: bool = False
    is_valid: bool = True


class IntelligentPublicationPreviewResponse(BaseModel):
    original_text: str
    strategy: Strategy
    is_variation_required: bool
    is_variation_applied: bool
    cache_hit: bool
    warning: str | None
    model: str | None
    prompt_version: str
    accounts: list[AccountPreviewResponse]
