# Custo de publicação por link — Especificação e estado implementado

Este documento registra a especificação oficial e o estado JÁ
IMPLEMENTADO da regra de custo diferenciado por conteúdo de post,
seguindo o mesmo formato de `docs/ROADMAP_MEDIA.md`,
`docs/ROADMAP_PRIMEIRO_ACESSO.md`, `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`
e `docs/ROADMAP_JITTER.md`. Trate o código como fonte da verdade em
caso de divergência futura com este documento.

## Objetivo

Publicações contendo link no texto consomem mais saldo do plano do que
publicações comuns, refletindo o maior valor/risco de um post com CTA
externo.

## Regra de negócio oficial

- Post cujo texto contenha pelo menos um link: **15 créditos por conta
  publicada com sucesso**.
- Qualquer outro post — texto simples ou com mídia (imagem/gif/vídeo)
  anexada, sem link no texto: **1 crédito por conta publicada com
  sucesso** (comportamento padrão já existente antes desta regra, sem
  nenhuma mudança).
- A mídia anexada **nunca** altera o custo — só a presença de link no
  **texto** do post importa.
- O custo é "por conta": um post com link publicado em N contas
  consome `15 * N` créditos no total, não um valor fixo por post
  independente da quantidade de contas — mesma lógica já usada para o
  caso padrão (1 crédito por conta).
- A classificação (tem link ou não) é feita **uma única vez por post**,
  sobre `Post.text` (o texto original) — nunca por conta
  individualmente, mesmo com Publicação Inteligente (ver "Decisão
  técnica" abaixo).

## Estado atual (antes desta implementação)

`app/domain/publication_cost.py` já existia como código preparatório
(`PublicationContentType`/`PublicationCostPolicy`, pesos TEXT=1,
IMAGE=1, VIDEO=1, LINK=15), mas nunca esteve conectado ao fluxo real —
`PostService.publish_post` sempre consumia exatamente 1 crédito por
conta, independente do conteúdo. Documentado como lacuna conhecida em
`claude.md` e na auditoria funcional (`docs/AUDITORIA_FUNCIONAL.md`).

## Arquitetura implementada

Preserva a arquitetura em camadas do XHub (`Routes -> Services ->
Repositories -> Models`), sem nenhuma rota/schema/model novo — a regra
inteira vive na camada de domínio e é consumida pelo service já
existente.

### Backend

- `app/domain/publication_cost.py` (reescrito)
  - `post_text_has_link(text) -> bool`: reaproveita
    `app.domain.content_invariants.extract_invariants(text).urls`
    (mesma detecção de URL já usada pela Publicação Inteligente — não
    uma implementação nova) para decidir se o texto contém um link.
  - `credits_per_account_for_post(text) -> int`: retorna
    `LINK_CREDITS_PER_ACCOUNT` (15) se houver link, senão
    `DEFAULT_CREDITS_PER_ACCOUNT` (1).
  - `PublicationContentType`/`PublicationCostPolicy`/
    `calculate_publication_cost` (modelo antigo, baseado em
    classificação mutuamente exclusiva TEXT/IMAGE/VIDEO/LINK) foram
    **removidos** — não refletiam a regra real (mídia e link não são
    categorias mutuamente exclusivas: um post pode ter mídia anexada
    **e** link no texto ao mesmo tempo). `PublicationContentType`
    removido de `app/domain/enums.py` por ficar sem nenhum uso após a
    reescrita.
- `app/services/post_service.py` (`PostService.publish_post`)
  - `credits_per_account = credits_per_account_for_post(post.text)`
    calculado uma única vez, logo antes da validação de saldo.
  - `subscription_service.ensure_can_publish(..., required_posts=len(accounts_to_publish) * credits_per_account)`
    — a validação de saldo suficiente (ANTES de qualquer chamada à API
    do X) agora reflete o custo real total da chamada, não mais um
    valor fixo de 1 por conta.
  - `subscription_service.consume_posts(subscription.id, credits_per_account)`
    — chamado uma vez por conta publicada com sucesso (dentro do loop
    já existente), consumindo o valor correto por conta.
  - Nenhuma outra parte do fluxo mudou: idempotência, Jitter, mídia,
    Publicação Inteligente, tratamento de falha e o commit imediato
    por conta continuam exatamente como antes.

### Frontend

- `src/lib/publicationCost.ts` (novo) — espelha a detecção de link do
  backend (`containsLink`) só para feedback instantâneo — o backend
  continua sendo a única fonte de verdade real.
- `src/pages/NewPostPage.tsx` — aviso visível quando o texto digitado
  contém um link, mostrando o custo por conta e o total para as contas
  selecionadas, para que o usuário nunca seja surpreendido pelo
  consumo maior de saldo.

## Decisão técnica — por que classificar uma única vez por `Post.text`

Com Publicação Inteligente, cada conta pode publicar um texto
diferente (`PostAccount.rendered_text`). Ainda assim, classificar pelo
texto **original** (`Post.text`) é suficiente e correto: toda variação
gerada pela IA (ou editada manualmente) é obrigada a preservar
exatamente os mesmos links do texto original
(`app.domain.content_invariants.preserves_invariants` — comparação por
multiset de URLs; uma variação que adicionasse ou removesse um link
seria descartada antes de chegar ao `Post`). Ou seja, nunca existe o
caso de uma conta de um mesmo post publicar um texto com link e outra
sem — a classificação "tem link" é uma propriedade real do post
inteiro, não apenas do texto original.

## Validação realizada

- `python -c "import app.main"`: aplicação importa sem erro.
- `pytest`: 6 passaram, 0 falharam (sem regressão).
- Script Python descartável dentro do container (removido após a
  validação, sem tocar a API real do X — `XOAuthClient` substituído por
  um dublê): função pura de detecção de link (URL completa, domínio
  sem esquema, encurtador, textos sem link); post sem link com 2 contas
  consome exatamente 2 créditos (1/conta); post com link e 2 contas
  consome exatamente 30 créditos (15/conta); saldo suficiente para o
  custo antigo (1/conta) mas insuficiente para o novo (15/conta) é
  corretamente bloqueado **antes de qualquer chamada ao X**; custo
  depende exclusivamente do texto, nunca de mídia anexada.
- Frontend: `tsc --noEmit` e `npm run build` limpos.

## Fora de escopo desta implementação

- Custo diferenciado adicional por outros critérios (ex.: múltiplos
  links, comprimento do link, domínio específico) — a regra oficial é
  binária (tem link ou não), sem gradação.
- Exibir o custo por conta na tela de confirmação
  (`PublishOrScheduleDialog`) ou no histórico de posts já publicados —
  o aviso no compositor (`NewPostPage`) já comunica o custo antes da
  publicação acontecer; replicar em mais telas não foi pedido.
