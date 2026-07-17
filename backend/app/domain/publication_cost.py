"""Calculo de custo de publicacao (em creditos do plano) por conta.

Regra oficial de negocio:
- Post cujo texto contenha pelo menos um link (URL): 15 creditos por
  conta publicada.
- Qualquer outro post -- texto simples ou com midia (imagem/gif/video)
  anexada, sem link no texto: 1 credito por conta publicada (o
  comportamento padrao ja existente antes desta regra).

A midia anexada (`Post.media`) NUNCA altera o custo -- so a presenca de
link no TEXTO do post importa. A classificacao e feita uma unica vez
por post, sobre `Post.text` (o texto original, nunca sobrescrito -- ver
`app.services.post_service.PostService.publish_post`), e vale
igualmente para todas as contas: a Publicacao Inteligente preserva
exatamente os links do texto original em toda variacao gerada (ver
`app.domain.content_invariants.preserves_invariants` -- uma variacao
que adicionasse ou removesse um link seria descartada antes mesmo de
chegar aqui), entao nunca existe o caso de uma conta publicar um texto
com link e outra do MESMO post sem.
"""

from __future__ import annotations

from app.domain.content_invariants import extract_invariants

# Creditos consumidos por conta publicada quando o texto do post NAO
# contem nenhum link -- o comportamento padrao, ja existente antes
# desta regra (texto simples ou com midia anexada).
DEFAULT_CREDITS_PER_ACCOUNT = 1

# Creditos consumidos por conta publicada quando o texto do post
# contem pelo menos um link. Um post com link publicado em N contas
# consome `LINK_CREDITS_PER_ACCOUNT * N` creditos no total -- mesma
# logica "por conta" ja usada para o caso padrao, nao um valor fixo por
# post independente do numero de contas.
LINK_CREDITS_PER_ACCOUNT = 15


def post_text_has_link(text: str) -> bool:
    """`True` se `text` contiver pelo menos uma URL (mesma deteccao
    usada pela preservacao de invariantes da Publicacao Inteligente --
    ver `app.domain.content_invariants.extract_invariants`)."""
    return len(extract_invariants(text).urls) > 0


def credits_per_account_for_post(text: str) -> int:
    """Creditos consumidos por CADA conta publicada com sucesso para um
    post com este texto -- `LINK_CREDITS_PER_ACCOUNT` se houver link,
    `DEFAULT_CREDITS_PER_ACCOUNT` caso contrario."""
    return LINK_CREDITS_PER_ACCOUNT if post_text_has_link(text) else DEFAULT_CREDITS_PER_ACCOUNT
