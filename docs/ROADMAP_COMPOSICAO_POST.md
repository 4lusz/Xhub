# Separação Fluxo 1 / Fluxo 2 de composição de post — XHub

## 1. Objetivo

Antes desta funcionalidade, o único jeito de um usuário publicar
conteúdo diferente por conta era "abusar" da Publicação Inteligente:
gerar uma variação (ou nem isso) e reescrever cada texto manualmente no
preview até ficarem completamente distintos entre si — mesmo que a
intenção não tivesse nada a ver com "variação natural do mesmo texto".
Isso deixava `Post.text` sem sentido real nesses casos (qual das N
versões era "o original"?) e fazia regras da Publicação Inteligente
(invariantes preservados, variação obrigatória em 5+ contas) se
aplicarem a um cenário para o qual elas nunca foram desenhadas.

Esta funcionalidade separa os dois casos de uso em modos explícitos,
decididos pelo usuário no início da criação do post:

- **Fluxo 1 (`composition_mode=SHARED`, comportamento histórico,
  default):** um único texto (`Post.text`), com Publicação Inteligente
  opcional/obrigatória por faixa de contas — inalterado.
- **Fluxo 2 (`composition_mode=INDEPENDENT`):** sem texto principal —
  cada conta selecionada escreve seu próprio tweet, manualmente, sem
  IA, desde o início. Mídia pode ser compartilhada entre todas as
  contas (padrão) ou individualizada por conta.

## 2. Regra de negócio

- `Post.composition_mode` é decidido na CRIAÇÃO do post e nunca
  inferido do conteúdo depois — inferir pelo conteúdo seria ambíguo
  (um Fluxo 1 com variações editadas até ficarem todas diferentes é
  indistinguível de um Fluxo 2 genuíno só olhando o texto salvo).
  Necessário para saber, ao reabrir/republicar, qual validação rodar,
  e para o `publish_post` saber se revalida a Publicação Inteligente.
- **SHARED:** `text` obrigatório, vira `Post.text`. `rendered_texts`
  continua opcional (Publicação Inteligente). Nenhuma mudança de
  comportamento em relação a antes desta funcionalidade.
- **INDEPENDENT:** `text` deve vir vazio/ausente (`Post.text` fica
  `NULL`). `rendered_texts` passa a ser OBRIGATÓRIO para TODA conta
  selecionada — cada uma com seu próprio tweet, sem relação entre si:
  nunca há invariantes a preservar (não existe "original"), nunca há
  obrigatoriedade de variação distinta em 5+ contas (não existe
  "variação" quando não existe uma base — duplicar texto entre contas é
  uma decisão manual do usuário, permitida).
- **Aviso de conteúdo duplicado (não bloqueia), nos dois modos:**
  quando 2+ contas selecionadas acabam com o mesmo texto fora do caso
  já bloqueado (Fluxo 1 com 5+ contas, variação obrigatória — esse
  continua um bloqueio, não um aviso), a interface mostra um alerta
  explicando o risco de detecção de conteúdo repetitivo pelo X, mas
  permite confirmar/criar o post assim mesmo. Decisão deliberada: um
  bloqueio automático reverteria decisões de produto já tomadas
  (variação é OPCIONAL em 2-4 contas; Fluxo 2 dá controle manual total
  ao usuário) — publicar o mesmo anúncio em poucas contas é um uso
  legítimo e comum. Ver `docs/AUDITORIA_SEGURANCA.md` (achado
  "Fluxo 2 contorna a proteção anti-detecção de 5+ contas").

## 3. Mídia — compartilhada ou por conta

`PostMedia.post_account_id` (nullable, FK para `post_accounts.id`):

- `NULL` = mídia compartilhada entre todas as contas do post (único
  caso possível no Fluxo 1; padrão também no Fluxo 2).
- Preenchido = mídia exclusiva daquela conta — só possível no Fluxo 2,
  quando o usuário desmarca "usar a mesma mídia em todos os tweets".

Na publicação, `PostMediaRepository.list_for_post_account` resolve os
dois casos com uma única query (`post_account_id IS NULL OR =
<conta>`) — a mesma função de validação de combinação de mídia
(`app.domain.media_rules.validate_media_combination`, inalterada) é
aplicada por GRUPO (uma vez se compartilhada, uma vez por conta se
individual), nunca uma regra nova.

`media_ids` (compartilhada) e `account_media_ids` (mapa `conta ->
media_ids`, individual) são mutuamente exclusivos — o usuário escolhe
um ou outro, nunca os dois. A mesma mídia não pode ser referenciada em
duas contas diferentes (validado explicitamente, ver seção 4).

## 4. Arquitetura implementada

- **`app/models/enums.py`** — `PostCompositionMode` (SHARED/INDEPENDENT).
  Não duplicado em `app.domain.enums` (diferente de `UserRole`/
  `SubscriptionStatus`) — as funções puras que precisam da regra usam
  tipos primitivos (bool/str), sem precisar do enum na camada de
  domínio.
- **`app/domain/post_composition.py`** — `find_accounts_missing_independent_text`,
  função pura: toda conta selecionada precisa ter texto próprio válido
  no modo INDEPENDENT.
- **`app/repositories/post_media_repository.py`** —
  `list_for_post_account` (bulk, compartilhada + individual);
  `attach_to_post` ganhou `post_account_id` opcional.
- **`app/services/post_service.py`**:
  - `create_post` bifurca por `composition_mode`: valida texto
    principal obrigatório/proibido, valida texto por conta
    obrigatório (INDEPENDENT) ou opcional com invariantes (SHARED),
    valida mídia compartilhada e/ou individual (`_validate_and_load_account_media`,
    que reaproveita `_validate_and_load_media` por conta e rejeita
    reuso da mesma mídia em contas diferentes).
  - `publish_post`: a checagem de variação obrigatória em 5+ contas só
    roda quando `composition_mode is SHARED`. Custo por conta
    (`credits_per_account_for_post`) passou a ser calculado a partir do
    texto EFETIVO de cada conta (`rendered_text or post.text`) em vez
    de uma única vez sobre `post.text` — no Fluxo 1 isso sempre dá o
    mesmo resultado pra todas as contas (invariantes garantem que toda
    variação preserva os mesmos links do original), mas no Fluxo 2 cada
    conta pode ter um custo diferente das demais.
- **`app/routes/post.py`** — `CreatePostRequest` ganhou
  `composition_mode`, `text` agora opcional, `account_media_ids`.
  `PostResponse`/`PostAccountResponse` expõem `composition_mode` e
  `rendered_text` (texto efetivo de cada conta, sempre presente no
  Fluxo 2). `PostMediaResponse` expõe `post_account_id`.
- **Frontend**:
  - `components/posts/IndependentPostComposer.tsx` — um editor de
    texto por conta selecionada + toggle "mesma mídia para todos" (com
    `ConfirmDialog` antes de limpar mídia já anexada ao trocar de
    modo) + aviso de texto duplicado entre contas.
  - `components/posts/AccountMediaEditor.tsx` — uma instância de
    `useMediaComposer` por conta (mídia individual), reportando estado
    pro componente pai via callback (múltiplas instâncias do hook não
    podem viver num componente só, contagem de contas é dinâmica).
  - `components/intelligent-publication/IntelligentPublicationPreviewModal.tsx` —
    aviso de texto duplicado (não bloqueante) fora do caso obrigatório
    de 5+ contas.
  - `pages/NewPostPage.tsx` — seletor de modo (`Tabs`), mantendo o
    Fluxo 1 exatamente como era antes.

## 5. Validação realizada

- Suíte `pytest` (6/6, sem regressão).
- Script descartável (removido após validar): 17 checagens cobrindo
  criação nos dois modos, texto faltando/proibido, mídia compartilhada
  vs. individual, reuso de mídia entre contas (rejeitado), cálculo de
  custo por texto com/sem link.
- Requisições HTTP reais contra o backend local: criação SHARED
  (regressão) e INDEPENDENT, rejeição de texto principal no modo
  INDEPENDENT — limpos após validar.
- `tsc -b` e `npm run build` limpos após cada etapa do frontend.
- Auditoria de segurança dedicada (ver
  `docs/AUDITORIA_SEGURANCA.md`) — 1 achado (bypass da proteção
  anti-detecção de 5+ contas via Fluxo 2), mitigado com aviso não
  bloqueante nos dois fluxos, decisão consciente documentada.

## 6. Fora de escopo desta implementação

- Reabrir um rascunho/agendamento para EDITAR o texto/mídia depois de
  criado — não existe hoje para nenhum dos dois fluxos (o app não tem
  tela de edição de post, só criação + publicar/agendar/excluir).
- Mídia individual por conta no Fluxo 1 — mídia continua
  obrigatoriamente compartilhada nesse modo, por design (só o texto
  varia lá).
