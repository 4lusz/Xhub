# CHANGELOG — Auditoria completa de segurança (frontend aprovado sem alteração)

Última auditoria do projeto antes de produção. Relatório técnico
completo em `docs/AUDITORIA_SEGURANCA.md`. O frontend foi auditado por
completo (XSS/DOM injection, armazenamento de tokens, guards de rota,
vazamento de informação) e **aprovado sem necessidade de nenhuma
alteração de código**:

- Nenhum `dangerouslySetInnerHTML`/`innerHTML`/`eval`/`document.write`
  em todo o código-fonte (busca direcionada, zero ocorrências) — React
  escapa JSX por padrão, sem vetor de XSS conhecido.
- Tokens (`accessToken`/`refreshToken`) ficam em `localStorage` via
  `zustand`/`persist` — aceito como trade-off arquitetural, sem risco
  concreto na ausência de XSS; mitigado do lado do backend com um
  `Content-Security-Policy` restritivo (ver `backend/CHANGELOG.md`).
- Guards de rota (`ProtectedRoute`/`AdminRoute`/`ClientOnlyRoute`) são
  UX pura — toda autorização real acontece no backend, então um bypass
  client-side (ex.: DevTools) nunca expõe dado que o backend não
  entregaria de qualquer forma.
- `npm audit` (produção e desenvolvimento): 0 vulnerabilidades
  conhecidas em toda a árvore de dependências.

# CHANGELOG — Aviso de custo por link no compositor de posts

Backend passou a cobrar 15 créditos por conta (em vez de 1) para posts
com link no texto (ver `backend/CHANGELOG.md` e
`docs/ROADMAP_CUSTO_LINK.md`). Para que o usuário nunca seja
surpreendido pelo consumo maior de saldo, o compositor de posts agora
avisa antes de publicar.

- `src/lib/publicationCost.ts` (novo) — espelha a detecção de link do
  backend (`containsLink`) só para feedback instantâneo; o backend
  continua sendo a única fonte de verdade real sobre o custo.
- `src/pages/NewPostPage.tsx` — aviso visível (mesmo padrão visual já
  usado para os avisos de Publicação Inteligente) quando o texto
  digitado contém um link, mostrando o custo por conta e o total para
  as contas selecionadas.

Validado: `tsc --noEmit` e `npm run build` limpos.

# CHANGELOG — Auditoria funcional completa

Validação de ponta a ponta de todo o frontend antes da auditoria de
segurança final. Relatório técnico completo em
`docs/AUDITORIA_FUNCIONAL.md`. Duas correções reais (sem funcionalidade
nova):

- **`pages/PostsPage.tsx`**: o botão "Excluir" ficava visível sempre
  que `post.status !== "published"` — mas esse é o status *agregado*
  do post; um post com falha parcial (`status === "failed"` com
  algumas contas `published` e outras `failed`) mostrava o botão
  mesmo tendo publicações reais associadas. Corrigido para checar
  `post.accounts.every(a => a.status !== "published")`, espelhando a
  nova validação do backend (`PostService.delete_post`, ver
  `backend/CHANGELOG.md`) que agora recusa (409) excluir qualquer post
  com ao menos uma conta publicada.
- **`pages/AccountsPage.tsx`**: o diálogo de confirmação ao desconectar
  uma conta do X afirmava "Posts já publicados não são afetados" — mas
  `TwitterAccount.post_accounts` tem cascade de exclusão no backend, e
  desconectar a conta apaga o histórico local dessas publicações
  (`PostAccount`, incluindo `x_post_id`), mesmo o tweet continuando
  publicado no X. Texto corrigido para descrever a consequência real,
  sem bloquear a ação (desconectar continua sendo permitido a qualquer
  momento, por ser uma ação legítima do usuário).

Validado: `tsc --noEmit` e `npm run build` limpos; revisão completa de
código de todas as páginas/componentes relevantes (estados de
loading/vazio/erro consistentes em toda a aplicação, nenhuma outra
inconsistência encontrada).

# CHANGELOG — Painel administrativo do Jitter

Tela administrativa para o sistema de Jitter implementado no backend
(ver CHANGELOG do backend e `docs/ROADMAP_JITTER.md`): atraso
aleatório entre publicações em contas diferentes de um mesmo post.
Nenhuma alteração na experiência do cliente final — o Jitter é
inteiramente transparente para quem publica.

## Novo

- `types/jitter.ts`, `services/jitter.ts`,
  `hooks/useAdminJitterSettings.ts`: tipos, chamadas HTTP
  (`GET`/`PATCH /admin/jitter-settings`) e hooks, mesmo padrão de
  `hooks/useAdminPlans.ts`.
- `pages/AdminJitterSettingsPage.tsx`: tela dedicada "Jitter" no menu
  administrativo (mesmo padrão visual de `AdminPlansPage.tsx`) —
  campos "Tempo mínimo (segundos)" e "Tempo máximo (segundos)",
  validados no cliente (min ≥ 0, max ≥ min, teto de 120s) espelhando
  as mesmas regras aplicadas pelo backend, antes de enviar.

## Alterado

- `components/layout/Sidebar.tsx`: novo item "Jitter" no menu
  administrativo (`/admin/jitter`).
- `App.tsx`: rota registrada.

## Validação

- `tsc --noEmit` e `npm run build` limpos, sem erros de tipo, 2271
  módulos.
- Servidor de desenvolvimento verificado via `curl` após restart:
  `AdminJitterSettingsPage.tsx` e `useAdminJitterSettings.ts`
  servidos (200); item "Jitter" confirmado no `Sidebar.tsx`; rota
  confirmada em `App.tsx`.
- Fluxo completo (leitura, validação de limites, atualização, efeito
  imediato na próxima publicação) validado ponta a ponta contra o
  backend real via `curl` (ver CHANGELOG do backend).
- **Não testado interativamente no navegador** nesta sessão — sem
  ferramenta de automação de browser disponível no ambiente.
  Recomenda-se clicar na tela "Jitter" antes de depender dela no dia
  a dia.

**Arquivos criados:** `types/jitter.ts`, `services/jitter.ts`,
`hooks/useAdminJitterSettings.ts`, `pages/AdminJitterSettingsPage.tsx`.

**Arquivos modificados:** `components/layout/Sidebar.tsx`, `App.tsx`.

---

# CHANGELOG — Correção: erro "[object Object]" e preço 0 ao editar plano

Reportado pelo usuário: `PATCH /admin/plans/{id}` falhava com 422 ao
salvar um plano com preço `0`, e o toast de erro mostrava
"[object Object]" em vez de uma mensagem legível.

**Causa raiz (validação divergente):**
`components/admin/EditPlanDialog.tsx` aceitava preço `>= 0`
(`z.coerce.number().min(0, ...)`), mas o backend sempre exigiu preço
`> 0` (`UpdatePlanRequest.price: float = Field(gt=0)`, ver
`app/routes/admin.py`) — o formulário deixava passar um valor que o
servidor sempre rejeitou. Corrigido para `min(0.01, "O preço deve ser
maior que zero.")`, espelhando a regra real do backend.

**Causa raiz ("[object Object]"):** bug sistêmico, não específico
deste formulário. Um 422 de validação do próprio Pydantic (antes de
chegar à rota) tem `detail` como uma LISTA de `{loc, msg, type}` — só
os erros de negócio (`BaseAppException`) do XHub têm `detail` como
string. `services/api.ts` passava `detail` direto para
`new ApiError(status, detail)`; atribuir um array a `Error.message`
vira a string `"[object Object]"` por coerção padrão do JS. Agora
`formatErrorDetail` (novo helper em `services/api.ts`) trata os dois
formatos, produzindo `"price: Input should be greater than 0"` em vez
disso — corrige esse erro em QUALQUER formulário do app, não só no de
planos.

**Validação:** `tsc --noEmit` e `npm run build` limpos; confirmado via
`curl` contra o backend real que `PATCH` com `price=0` retorna 422 com
o array de detalhe, e que `price=49.9` salva normalmente (200).

**Arquivos modificados:** `types/api.ts`, `services/api.ts`,
`components/admin/EditPlanDialog.tsx`.

---

# CHANGELOG — Primeiro acesso obrigatório (troca de senha temporária)

Tela e fluxo para a funcionalidade de segurança implementada no
backend (ver CHANGELOG do backend e `docs/ROADMAP_PRIMEIRO_ACESSO.md`):
toda conta criada por um administrador usa uma senha temporária até o
primeiro login, quando o usuário é obrigado a defini-la de novo antes
de acessar qualquer tela do sistema.

## Novo

- `pages/FirstAccessPage.tsx`: tela dedicada, deliberadamente distinta
  da tela de login — ícone de escudo, explicação explícita do motivo
  de segurança, aviso de que a etapa é obrigatória e única. Campos
  "Nova senha" e "Confirmar nova senha" com validação de
  correspondência (zod).
- `components/admin/ResetPasswordResultDialog.tsx`: exibe a senha
  temporária gerada por uma redefinição administrativa — uma única
  vez, com botão de copiar, nunca recuperável depois de fechado.

## Alterado

- `stores/authStore.ts`: novo estado persistido `mustChangePassword`
  (localStorage) — `ProtectedRoute` precisa decidir o redirecionamento
  de forma síncrona, inclusive logo após um F5, antes de qualquer
  chamada que ficaria bloqueada com 428 no backend. Atualizado em todo
  login/refresh e ao concluir a troca.
- `routes/ProtectedRoute.tsx`: redireciona para `/first-access`
  enquanto a troca estiver pendente — nenhuma outra tela do sistema é
  alcançável antes disso; redireciona de volta para `/` se o usuário
  tentar acessar `/first-access` sem precisar.
- `services/api.ts`: interceptor trata HTTP 428 como rede de segurança
  (sincroniza a flag e redireciona), complementando o gate do
  roteamento para o caso de a flag local estar desatualizada (ex.:
  uma redefinição administrativa concorrente).
- `services/auth.ts`, `hooks/useAuth.ts`: `changePassword` /
  `useChangePassword` (limpa a flag local e navega para `/` ao
  suceder).
- `pages/AdminUsersPage.tsx`: ação "Redefinir senha" no menu de cada
  usuário; badge "Aguardando 1º acesso" na listagem quando aplicável.
- `components/admin/CreateUserDialog.tsx`: campo renomeado de "Senha
  inicial" para "Senha temporária", com nota explicando a troca
  obrigatória no primeiro login.
- `types/auth.ts`, `types/user.ts`: `must_change_password` em
  `TokenResponse`/`User`; novo tipo `ResetPasswordResult`.

## Validação

- `tsc --noEmit` e `npm run build` limpos, sem erros de tipo, 2268
  módulos.
- Servidor de desenvolvimento verificado via `curl` após restart:
  `FirstAccessPage.tsx` e `ResetPasswordResultDialog.tsx` servidos
  (200); `ProtectedRoute.tsx`/`App.tsx` confirmados com o gate.
- Fluxo completo (criação → primeiro login → 428 → troca → login com
  senha nova → redefinição administrativa → novo ciclo) validado
  ponta a ponta contra o backend real via `curl` (ver CHANGELOG do
  backend).
- **Não testado interativamente no navegador** nesta sessão — sem
  ferramenta de automação de browser disponível no ambiente.
  Recomenda-se clicar na interface (tela de primeiro acesso e dialog
  de redefinição administrativa) antes do primeiro uso em produção.

**Arquivos criados:** `pages/FirstAccessPage.tsx`,
`components/admin/ResetPasswordResultDialog.tsx`.

**Arquivos modificados:** `types/auth.ts`, `types/user.ts`,
`stores/authStore.ts`, `services/auth.ts`, `services/api.ts`,
`services/users.ts`, `hooks/useAuth.ts`, `hooks/useAdminUsers.ts`,
`routes/ProtectedRoute.tsx`, `App.tsx`, `pages/AdminUsersPage.tsx`,
`components/admin/CreateUserDialog.tsx`.

---

# CHANGELOG — Editor de mídia completo: crop/zoom/rotação de imagem, corte real de vídeo, visualizador em tela cheia

Evolução do compositor de mídia (ver CHANGELOG anterior) a pedido do
usuário: o preview em miniatura não era suficiente para quem depende de
mídia com qualidade final (propagandas, vídeos de clientes). Adiciona
edição de verdade — tudo 100% no navegador, sem processamento novo no
backend, decisão explícita do usuário.

## Edição de imagem (crop + zoom + rotação)

- `lib/imageCrop.ts`: gera a imagem final via canvas (recorte + giro),
  mesmo padrão de referência do `react-easy-crop`.
- `components/posts/ImageEditorDialog.tsx`: recorte arrastável/
  redimensionável, zoom (slider), rotação (slider + botões de 90°),
  presets de proporção (Original, Quadrado, Retrato 4:5, Paisagem
  16:9). Nunca oferecido para GIF (canvas destruiria a animação).
- Nova dependência: `react-easy-crop` (leve, sem processamento
  server-side).

## Corte real de vídeo (trim)

- `hooks/useFfmpeg.ts`: corte de vídeo de verdade rodando
  **inteiramente no navegador** via `ffmpeg.wasm` (`-c copy`, sem
  recodificar — rápido mesmo para arquivos grandes; o corte encaixa no
  keyframe mais próximo, variação de ~1-2s é esperada e documentada).
  O core (`ffmpeg-core.js`/`.wasm`, ~30MB) é **self-hosted** em
  `public/ffmpeg/` (copiado do pacote via `scripts/copy-ffmpeg-core.mjs`,
  rodado automaticamente no `postinstall`) — nunca carregado de um CDN
  de terceiros, e só baixado na primeira vez que o usuário abre o
  editor de vídeo.
- `components/posts/VideoTrimmerDialog.tsx`: player com preview,
  marcadores de início/fim arrastáveis, barra de progresso durante o
  processamento.
- Novas dependências: `@ffmpeg/ffmpeg`, `@ffmpeg/core`, `@ffmpeg/util`.
  **Decisão explícita do usuário:** nenhum processamento no backend —
  o backend continua recebendo só o arquivo final já cortado, como
  qualquer outro upload.

## Visualizador completo (`MediaLightbox`)

- `components/posts/MediaLightbox.tsx`: clique em qualquer miniatura
  abre uma visualização em tela cheia — zoom + pan em imagens/gifs
  (scroll ou botões, arrastar quando ampliado), player nativo completo
  para vídeo (controles, barra de progresso, volume, fullscreen já
  embutidos pelo navegador), navegação entre as mídias anexadas ao
  mesmo post (setas, teclado, indicadores de página), botão de editar
  sem precisar fechar e reabrir.

## Edição não destrutiva

- `hooks/useMediaComposer.ts`: cada item guarda `originalFile` (o
  arquivo pristino, nunca sobrescrito). Reeditar sempre parte do
  original — evita degradar qualidade a cada edição sucessiva. Ao
  aplicar uma edição, o upload antigo é removido do backend
  (`DELETE /media/{id}`) e o novo arquivo é enviado, mantendo a mesma
  posição no post.
- `components/posts/MediaComposer.tsx`: botão de editar (lápis) e de
  remover por miniatura (hover); clique na própria miniatura abre o
  lightbox.

## Nova dependência de UI

- `components/ui/slider.tsx` (novo primitivo, `@radix-ui/react-slider`)
  — usado no zoom/rotação da imagem e nos marcadores de corte do
  vídeo, seguindo o mesmo padrão dos demais primitivos em
  `components/ui/`.

## Validação

- `tsc --noEmit` e `npm run build` limpos (2266 módulos) após corrigir
  um erro de tipo (`ArrayBufferLike` vs `ArrayBuffer` no retorno do
  `ffmpeg.readFile`, resolvido copiando para um `Uint8Array` comum).
- Servidor de desenvolvimento verificado via `curl` após restart:
  todos os componentes novos servidos (200), `ffmpeg-core.js` (112KB)
  e `ffmpeg-core.wasm` (32MB) servidos como assets estáticos do mesmo
  origin.
- **Não testado interativamente nesta sessão** — sem navegador
  automatizado disponível no ambiente (verificado: sem Chromium/
  Playwright instalado; optei por não instalar um headless browser às
  pressas dado o risco de falha/tempo em um ambiente não preparado
  para isso). A validação foi inteiramente estática (tipos, build,
  assets servidos). Recomenda-se testar manualmente: abrir o editor de
  imagem e aplicar um recorte, abrir o editor de vídeo (primeira vez
  carrega ~30MB do ffmpeg-core, pode levar alguns segundos) e cortar,
  abrir o lightbox e navegar entre múltiplos arquivos.

**Arquivos criados:** `lib/imageCrop.ts`,
`components/posts/ImageEditorDialog.tsx`, `hooks/useFfmpeg.ts`,
`components/posts/VideoTrimmerDialog.tsx`,
`components/posts/MediaLightbox.tsx`, `components/ui/slider.tsx`,
`scripts/copy-ffmpeg-core.mjs`.

**Arquivos modificados:** `hooks/useMediaComposer.ts`,
`components/posts/MediaComposer.tsx`, `pages/NewPostPage.tsx`,
`package.json`.

---

# CHANGELOG — Suporte completo a mídia (imagem/gif/vídeo) no compositor de post

Mídia integrada na MESMA tela de criação de post (não uma tela
separada), no espírito do compositor do X: escrever o texto, anexar
imagens/gif/vídeo com preview imediato e, opcionalmente, usar a
Publicação Inteligente — que continua atuando só sobre o texto, nunca
sobre a mídia. Detalhes técnicos completos em
`docs/ROADMAP_MEDIA.md`.

## Novo

- `types/media.ts`, `services/media.ts`: tipos e chamadas HTTP
  (`POST /media/upload` multipart, `DELETE /media/{id}`).
- `lib/mediaRules.ts`: espelha `app/domain/media_rules.py` (tipos
  aceitos, limites de tamanho, combinação válida) para feedback
  instantâneo no navegador — o backend continua sendo a única fonte de
  verdade, revalidando tudo de novo.
- `hooks/useMediaUpload.ts` (mutations cruas) e
  `hooks/useMediaComposer.ts` (estado do compositor): cada arquivo
  selecionado ganha preview LOCAL instantâneo
  (`URL.createObjectURL(file)`, sem round-trip ao backend) enquanto o
  upload roda em paralelo; remover um item já enviado dispara a
  remoção no backend; limpa os object URLs ao desmontar/reset.
- `components/posts/MediaComposer.tsx`: botões de anexar imagem/gif e
  vídeo logo abaixo do texto (mesma tela), grade de preview com
  remoção por hover, indicador de upload em andamento e de erro por
  item.

## Alterado

- `pages/NewPostPage.tsx`: `MediaComposer` inserido logo abaixo do
  textarea; `media_ids` (apenas uploads concluídos) enviado junto da
  confirmação do post; botão de gerar Publicação Inteligente
  desabilitado enquanto houver upload em andamento ou com erro; reset
  do compositor ao salvar/publicar.
- `components/intelligent-publication/IntelligentPublicationPreviewModal.tsx`:
  nova nota (quando há mídia anexada) explicando que ela será
  publicada exatamente igual em todas as contas — só o texto varia.
- `types/post.ts`: `CreatePostPayload.media_ids` (opcional) e
  `Post.media`.

## Contas conectadas — foto de perfil real e @username como identificador principal

- `types/twitterAccount.ts`: novo campo `profile_image_url`.
- `components/accounts/TwitterAccountCard.tsx`,
  `components/posts/AccountSelector.tsx`: `AvatarImage` com a foto
  real da conta (fallback automático para as iniciais quando `null` —
  contas conectadas antes desta mudança, até serem reconectadas);
  `@username` passou a ser o texto em destaque (identificador
  principal), com `display_name` como informação secundária — antes
  era o oposto.

## Validação

- `tsc --noEmit` e `npm run build` (`tsc -b && vite build`) limpos,
  sem erros de tipo, 2243 módulos.
- Servidor de desenvolvimento verificado via `curl` após restart do
  container (o watcher do Vite nem sempre propaga mudanças de bind
  mount neste ambiente, padrão já observado em sessões anteriores):
  `NewPostPage.tsx` referencia `MediaComposer`, `TwitterAccountCard.tsx`
  usa `AvatarImage`.
- Fluxo completo de upload/preview/remoção validado contra o backend
  real via `curl` (ver CHANGELOG do backend) — upload, download
  autenticado e remoção funcionando ponta a ponta.

**Arquivos criados:** `types/media.ts`, `services/media.ts`,
`lib/mediaRules.ts`, `hooks/useMediaUpload.ts`,
`hooks/useMediaComposer.ts`, `components/posts/MediaComposer.tsx`.

**Arquivos modificados:** `pages/NewPostPage.tsx`,
`components/intelligent-publication/IntelligentPublicationPreviewModal.tsx`,
`components/accounts/TwitterAccountCard.tsx`,
`components/posts/AccountSelector.tsx`, `types/post.ts`,
`types/twitterAccount.ts`.

---

# CHANGELOG — Auditoria técnica da Publicação Inteligente: comentários desatualizados

Parte da auditoria completa do fluxo (ver CHANGELOG do backend para as
correções de prompt/validação). No frontend, o único achado foi
documentação obsoleta, sem nenhum bug de comportamento:

`hooks/useIntelligentPublication.ts` e `services/intelligentPublication.ts`
tinham docstrings dizendo que o fluxo "ainda não foi implementado no
frontend" e mostrando um exemplo de uso hipotético -- desatualizado desde
que `pages/NewPostPage.tsx` passou a consumir os dois de verdade. Comentário
enganoso para quem for ler o código depois achando que a feature não existe.
Atualizado para descrever o uso real (consumido por `NewPostPage.tsx`).

**Arquivos:** `hooks/useIntelligentPublication.ts`, `services/intelligentPublication.ts`.

## Validação

- `tsc -b && vite build` limpo (2238 módulos) -- mudança é só comentário,
  nenhum código de execução foi alterado.

---

# CHANGELOG — UX da Publicação Inteligente: comunicação clara, sem tocar em lógica

Melhoria exclusivamente de copy/UX no fluxo de Publicação Inteligente,
conforme pedido explícito: nenhuma alteração de arquitetura, regra de
negócio ou integração com o backend (nenhum arquivo do backend, tipo de
API ou chamada HTTP foi alterado nesta rodada).

## 1. Botão de disparo deixa de soar como "preview genérico"

`pages/NewPostPage.tsx`: botão renomeado de "Gerar preview" para
**"Gerar Publicação Inteligente"** — deixa claro, antes mesmo de abrir
o modal, que a ação aciona a funcionalidade de IA do XHub.

## 2. Modal explica o que está acontecendo, com precisão

`components/intelligent-publication/IntelligentPublicationPreviewModal.tsx`:

- **Explicação geral fixa** (nova `DialogDescription`): "Nossa IA
  reescreve seu texto em variações naturais, preservando o significado,
  links, hashtags e menções — o objetivo é reduzir padrões repetitivos
  entre contas e diminuir o risco de bloqueio pela política do X."
- **Resumo situacional** (novo bloco com ícone, logo abaixo): explica o
  que aconteceu *nesta* publicação especificamente, cobrindo os 4
  estados reais que o backend pode retornar (espelhados fielmente de
  `app/services/ai_content_variation_service.py`, nenhum inventado):
  1. 1 conta → texto original, Publicação Inteligente não atua;
  2. 2-4 contas com variação aplicada → uma versão diferente por conta;
  3. 2-4 contas com variação desativada/indisponível → mesmo texto em
     todas (complementa, sem repetir, o aviso de risco já existente);
  4. 5+ contas → variação obrigatória, sem repetição entre elas.

Nenhuma prop nova veio do backend -- a lógica usa exatamente os campos
que a API já retornava (`strategy`, `is_variation_applied`).

## 3. Fluxo de publicar/agendar: mesma lógica, hierarquia mais clara

`components/posts/PublishOrScheduleDialog.tsx`: título e descrição
reforçam que o texto revisado na Publicação Inteligente já foi salvo;
adicionado um divisor "ou" entre "Publicar agora" e "Agendar", deixando
as duas ações visualmente como alternativas de mesmo nível (antes, a
segunda parecia um apêndice da primeira). Nenhuma etapa nova, nenhum
campo novo, nenhuma mudança de comportamento -- só reorganização visual
e copy mais precisa ("Deixar como rascunho por agora" no lugar de
"Deixar como rascunho", deixando claro que nada é perdido).

**Análise sobre reestruturar mais a fundo:** considerei usar abas
("Agora" / "Agendar") no lugar do botão + caixa atual, mas descartei --
seria mudança estrutural sem ganho real de clareza, e o pedido foi
manter a simplicidade sem aumentar etapas. A hierarquia visual atual
(ação primária grande e em destaque, alternativa clara logo abaixo) já
comunica bem a escolha; o ajuste ficou restrito a copy e ao divisor.

## Validação

- `tsc -b && vite build` limpo (2238 módulos).
- Conferido cada texto situacional contra o código real do backend que
  determina `strategy`/`is_variation_applied`, para garantir que nenhuma
  frase descreve um comportamento que a aplicação não tem.

---

# CHANGELOG — Privacidade em /admin/posts + busca por conta/usuário

Dois ajustes sobre a tela "Publicações" da rodada anterior:

## 1. Conteúdo do post removido da visão admin

`types/admin.ts::AdminPost` não tem mais o campo `text` (o backend
parou de retorná-lo). Coluna "Texto" removida da tabela em
`AdminPostsPage.tsx` -- o admin vê só status e o motivo de falha por
conta, nunca o que foi escrito.

## 2. Busca por conta/usuário + atalho a partir de Usuários

Campo de busca em `AdminPostsPage.tsx` que filtra (sobre a página
atual) por nome, e-mail ou `@usuário` do X -- responde ao pedido de
"acessar os posts de cada conta". `AdminUsersPage.tsx` ganhou um botão
"Posts" por linha, que leva direto para `/admin/posts?q={email}` com a
busca já preenchida e a aba em "Todos" (em vez do padrão "Falharam"),
para não esconder posts sem falha daquele usuário.

**Arquivos:** `types/admin.ts`, `pages/AdminPostsPage.tsx`,
`pages/AdminUsersPage.tsx`.

## Validação

- `tsc -b && vite build` limpo.
- Confirmado via OpenAPI e chamada real que `text` não existe mais na
  resposta de `GET /admin/posts`.

---

# CHANGELOG — Tela administrativa de publicações (motivo detalhado de falha)

Consome o novo `GET /admin/posts` do backend (ver CHANGELOG do backend
para o detalhe de como o motivo exato da falha passou a ser capturado).

## 1. `error_message` removido da visão do cliente

`types/post.ts::PostAccount` não tem mais o campo `error_message` (o
backend parou de retorná-lo em `GET /posts`). `PostAccountsBreakdown.tsx`
(tooltip por conta no histórico) ajustado para não tentar mais exibi-lo
— mostra só o status (`Publicado`/`Falhou`/`Pendente`), sem o motivo
técnico, que agora é exclusivo da visão administrativa.

**Arquivos:** `types/post.ts`, `components/posts/PostAccountsBreakdown.tsx`.

## 2. Nova tela "Publicações" no painel administrativo

`pages/AdminPostsPage.tsx` (`/admin/posts`): tabela com posts de todos
os usuários (data/hora, usuário, texto truncado, status, e por conta —
usuário do X + status + motivo exato da falha quando houver), com abas
de filtro (Falharam/Todos/Publicados/Pendentes/Agendados, padrão
"Falharam") e paginação anterior/próxima, no mesmo padrão de
`AdminAuditLogsPage`. Item "Publicações" adicionado ao menu do admin.

**Arquivos:** `types/admin.ts`, `services/admin.ts`,
`hooks/useAdminPosts.ts` (novo), `pages/AdminPostsPage.tsx` (novo),
`components/layout/Sidebar.tsx`, `App.tsx`.

## Validação

- `tsc -b && vite build` limpo (2238 módulos).
- Testado ao vivo: uma falha de publicação real (conta do X sem
  créditos) apareceu em `/admin/posts` com o motivo exato
  (`402 - Falha ao publicar no X: Payment Required: credits depleted`)
  — e não aparece mais em `error_message` nenhum lugar acessível pelo
  cliente.

---

# CHANGELOG — Auditoria funcional de produto: navegação admin/cliente, bugs de HTML e consumo do usuário

Auditoria completa de produto (não só técnica): navegação, regras de
negócio, integração com o backend e UX, cobrindo tanto a persona
administrador quanto cliente. Ver também o CHANGELOG do backend — um bug
crítico de migration foi encontrado e corrigido lá durante os testes de
ponta a ponta desta auditoria.

## 1. Administrador não usa mais telas de cliente (decisão arquitetural)

**Problema identificado:** o administrador tinha acesso a Dashboard,
Contas do X, Histórico, Novo post e Agendamentos — as mesmas telas do
cliente. Análise: contas admin são criadas **sem assinatura** por design
(`POST /admin/users` só cria `Subscription` quando o papel resultante
precisa dela para operar o produto como cliente) — na prática, qualquer
tentativa de conectar conta ou publicar por um admin já era rejeitada pelo
backend ("Usuario nao possui assinatura ativa"). As telas existiam, mas
terminavam em erro. Concordamos com a avaliação: administrador existe para
administrar, não para usar a plataforma como cliente.

**Solução:**
- Novo guard `routes/ClientOnlyRoute.tsx` (espelha `AdminRoute.tsx`, no
  sentido oposto): redireciona admin para `/admin` ao tentar acessar `/`,
  `/accounts`, `/posts`, `/posts/new` ou `/scheduled` — por navegação de
  menu ou digitando a URL diretamente.
  `App.tsx` envolve essas 5 rotas com o novo guard.
- `components/layout/Sidebar.tsx`: para `isAdmin`, o menu mostra
  exclusivamente Painel/Usuários/Planos/Auditoria (mais Perfil/Configurações,
  compartilhadas) — sem Dashboard/Contas/Histórico/Agendamentos, sem o botão
  "Novo post". O login de um admin agora cai direto em `/admin`, já que a
  raiz `/` está sob `ClientOnlyRoute`.
- `/profile` e `/settings` continuam compartilhadas entre as duas personas
  (fazem sentido para qualquer usuário; o card de plano em Configurações
  já se esconde sozinho para admin via `isError` do `/me/subscription`).

**Arquivos:** `routes/ClientOnlyRoute.tsx` (novo), `App.tsx`,
`components/layout/Sidebar.tsx`.

## 2. Consumo do usuário incompleto na tela de assinatura do admin

**Problema:** `SubscriptionActionsDialog` mostrava `used_posts`/`extra_posts`
crus, sem o limite do plano para comparação e sem contas conectadas — o
admin não conseguia avaliar se um usuário estava perto do limite (item
citado explicitamente na auditoria: "visualização do consumo do usuário").

**Solução:** consumindo os novos campos do backend
(`plan`/`used_accounts`/`available_posts`, ver CHANGELOG do backend), o
diálogo agora mostra nome do plano, "Contas do X: usadas/limite" e "Posts
usados: usados/limite (N restantes)".

**Arquivos:** `types/plan.ts`, `components/admin/SubscriptionActionsDialog.tsx`.

## 3. Bug de HTML inválido: `<div>` dentro de `<p>`

**Problema:** `StatCard` e o `SubscriptionStat` local de
`AdminDashboardPage` recebem `value` como `ReactNode` e o renderizavam
dentro de um `<p>` — quando `value` é um `<Skeleton />` (que é um `<div>`)
durante o carregamento, o React emite o warning "`<div>` cannot be a
descendant of `<p>`". Achado nos dois lugares onde o padrão se repetia.

**Solução:** trocado `<p>` por `<div>` no wrapper do valor em ambos os
componentes — semanticamente correto, já que não é texto de parágrafo, é um
número de estatística que pode conter qualquer `ReactNode`.

**Arquivos:** `components/dashboard/StatCard.tsx`, `pages/AdminDashboardPage.tsx`.

## 4. `GET /me/subscription` 404 — investigado, sem alteração de código

Confirmado ao vivo (rota registrada corretamente, path do frontend correto)
que o 404 é esperado para contas admin (sem assinatura por design) e que
contas cliente funcionam normalmente. A causa da confusão original foi o
bug crítico de migration corrigido no backend (impedia criar qualquer
cliente novo para testar) — ver CHANGELOG do backend.

## 5. Anexo de mídia em posts — não implementado (decisão documentada)

**Pedido:** permitir anexar imagem/vídeo na criação de post, "conforme
funcionalidades suportadas pelo backend".

**Decisão: não implementado.** O backend não suporta mídia em nenhum nível
— `Post`/`PostAccount` só têm campo de texto, `CreatePostRequest` só aceita
`text`, e a publicação real via `POST /posts/{id}/publish` chama a API do X
apenas com texto. `app/domain/publication_cost.py` (não importado por
nenhum código funcional) já documenta explicitamente: "suporte real a
imagem/video/link ainda [não existe]". O próprio
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md` lista "Suporte a imagem/video/link"
em **"Estratégia para futuras evoluções"** — future scope explícito, não
gap atual. Construir upload de mídia no frontend sem endpoint real violaria
a regra do projeto (`.continue/rules/03-frontend-react.md`: "Não crie telas
ou fluxos fictícios sem API correspondente"). Isso exigiria infraestrutura
nova real (storage de arquivo, novo endpoint multipart, e a API de mídia do
X é **separada** da de tweets — upload em chunks via INIT/APPEND/FINALIZE,
não o endpoint `POST /2/tweets` usado hoje) — um épico à parte, não algo a
improvisar dentro de uma auditoria.

## 6. Integração frontend↔backend: auditoria completa, sem gaps

Levantamento de todas as 43 rotas do backend (via introspecção de
`app.routes`) contra todo `services/*.ts`: cobertura completa — nenhum
endpoint implementado ficou sem tela, nenhum componente chama endpoint
inexistente. Únicos achados menores: `services/users.ts::getUser` e
`services/subscriptions.ts::getSubscription` (por id de assinatura, não por
usuário) são funções que chamam endpoints reais mas não são usadas por
nenhuma tela hoje — código morto inofensivo, não uma inconsistência (as
rotas que elas chamam existem e funcionam); não removido nesta rodada por
não ser o foco da auditoria.

## Validação

- `tsc -b && vite build` limpo dentro do container Docker após cada mudança
  (2236 módulos, sem erros de tipo).
- Ciclo completo testado ao vivo contra Postgres real (ver CHANGELOG do
  backend): criar admin → criar cliente com plano → login como cliente →
  `/me/subscription` (200) → `/admin/users/{id}/subscription` como admin
  (200, com plano/limites/consumo).
- **Não foi possível validar visualmente em navegador real** neste
  ambiente (sem `chromium-cli`/Playwright disponível e a instalação sob
  demanda não completou a tempo) — a navegação condicional por papel
  (`ClientOnlyRoute`/`Sidebar`) foi verificada por leitura de código e
  segue exatamente o mesmo padrão do `AdminRoute` já em produção, mas
  recomenda-se uma checagem manual rápida (login como admin, conferir que
  a sidebar não mostra telas de cliente e que `/accounts` redireciona para
  `/admin`) antes de considerar este item encerrado.

---

# CHANGELOG — Auditoria de frontend: responsividade, acessibilidade, perfil, indicadores e telas administrativas

Esta rodada implementa os 7 itens pendentes da auditoria de frontend,
seguindo os padrões já consolidados (Tailwind + tokens, primitivos em
`components/ui`, fluxo service → hook (TanStack Query) → página). Três
itens exigiram endpoints novos no backend (ver o CHANGELOG do backend);
os demais são só frontend. Nada do que já funcionava foi alterado.

## 1. Limpeza de código morto

Removidos 4 arquivos órfãos (confirmado por busca: nenhum import em lugar
nenhum): `components/StatusCard.tsx`, `components/IntelligentPublicationPreviewModal.tsx`
(a versão antiga na raiz — a em uso continua em
`components/intelligent-publication/`), `hooks/useAdminProbe.ts` e
`lib/scheduledPostCache.ts`.

## 2. Sidebar responsiva

A `Sidebar` era fixa (`w-64`, sem classes responsivas) e quebrava em
telas pequenas. Agora:
- Novo primitivo `components/ui/sheet.tsx` (shadcn Sheet sobre
  `@radix-ui/react-dialog`, já no projeto — sem biblioteca nova), com
  variantes de lado via `cva`, no mesmo padrão do `dialog.tsx`.
- `Sidebar.tsx` extrai o conteúdo em `SidebarNav` (compartilhado), expõe
  a `Sidebar` de desktop (`hidden md:flex`) e um novo `MobileSidebar`
  (botão hambúrguer + drawer que abre por cima do conteúdo e fecha ao
  navegar).
- `DashboardLayout.tsx` renderiza o hambúrguer no header em mobile e
  ajusta o padding (`px-4` → `sm:px-8`).

**Arquivos:** `components/ui/sheet.tsx` (novo), `components/layout/Sidebar.tsx`,
`layouts/DashboardLayout.tsx`.

## 3. Acessibilidade — `aria-label` em botões icon-only

Busca por `size="icon"` e botões cujo único conteúdo é um ícone. Rótulos
adicionados aos menus de três pontinhos (`TwitterAccountCard`,
`PostRow`), ao gatilho do menu da conta (`UserMenu`, só um avatar) e ao
hambúrguer da sidebar. Os botões de fechar de diálogos/sheet já traziam
`sr-only "Fechar"`.

**Arquivos:** `components/accounts/TwitterAccountCard.tsx`,
`components/posts/PostRow.tsx`, `components/layout/UserMenu.tsx`,
`components/layout/Sidebar.tsx`.

## 4. Perfil separado de Configurações

- Nova `pages/ProfilePage.tsx` (`/profile`): nome/e-mail/ID/papel via
  `useCurrentUser` (`GET /auth/me`), com aviso explícito de que a edição
  de nome/e-mail/senha **ainda não está disponível** (não há endpoint no
  backend — nenhum formulário falso).
- `SettingsPage.tsx` deixa de duplicar os dados de identidade e passa a
  focar em sessão/logout (+ indicador de plano, item 5).
- `UserMenu` ganhou atalhos "Perfil" e "Configurações"; a sidebar lista
  as duas telas.

**Arquivos:** `pages/ProfilePage.tsx` (novo), `pages/SettingsPage.tsx`,
`components/layout/UserMenu.tsx`, `components/layout/Sidebar.tsx`, `App.tsx`.

## 5. Indicador de plano/créditos do cliente

Consome o novo `GET /me/subscription`:
- `types/plan.ts::MySubscription`, `services/subscriptions.ts::getMySubscription`,
  `hooks/useMySubscription.ts` (`retry: false` — 404 esperado para admin,
  o indicador simplesmente não aparece).
- `components/dashboard/SubscriptionCard.tsx`: plano vigente, barra de
  progresso de posts usados/limite (com extras) e de contas usadas/limite,
  e data de vigência. Exibido no **Dashboard** e em **Configurações**.

**Arquivos:** `types/plan.ts`, `services/subscriptions.ts`,
`hooks/useMySubscription.ts` (novo), `components/dashboard/SubscriptionCard.tsx`
(novo), `pages/DashboardPage.tsx`, `pages/SettingsPage.tsx`.

## 6. Dashboard administrativo

Consome o novo `GET /admin/stats`. Nova `pages/AdminDashboardPage.tsx`
(`/admin`, index do painel): cards de total de usuários, assinaturas
ativas, posts no sistema e publicados, mais um bloco de assinaturas por
status (ativas/bloqueadas/expiradas). É só leitura — a criação de
usuários e a escolha de plano continuam em `/admin/users`.

**Arquivos:** `types/admin.ts` (novo), `services/admin.ts` (novo),
`hooks/useAdminStats.ts` (novo), `pages/AdminDashboardPage.tsx` (novo),
`components/layout/Sidebar.tsx`, `App.tsx`.

## 7. Auditoria

Consome o novo `GET /admin/audit-logs`. Nova `pages/AdminAuditLogsPage.tsx`
(`/admin/audit-logs`): tabela (data/hora, ação, autor, alvo, descrição)
no mesmo padrão de `/admin/users`, com ações traduzidas para pt-BR e
paginação "anterior/próxima" (`keepPreviousData`, já que o backend não
expõe contagem total).

**Arquivos:** `types/admin.ts`, `services/admin.ts`,
`hooks/useAuditLogs.ts` (novo), `pages/AdminAuditLogsPage.tsx` (novo),
`components/layout/Sidebar.tsx`, `App.tsx`.

## Validação

- `npm run build` (`tsc -b && vite build`) passa limpo após cada item e
  no fim (dependências instaladas via `npm install`; o único aviso é o
  pré-existente de tamanho de chunk).
- Backend: as 3 rotas novas importam e registram sem erro (ver CHANGELOG
  do backend).

---

# CHANGELOG — Correções pós-revisão (integração com os endpoints novos do backend)

Esta rodada resolve todos os pontos levantados na revisão completa do
frontend, depois que o backend passou a expor 5 endpoints/ajustes novos.
Nenhum arquivo do backend foi alterado nesta rodada — todas as mudanças são
no frontend, consumindo o que já existe.

## 1. Conectar conta do X (crítico — estava quebrado)

**Problema:** `GET /oauth/x/login` passou a retornar
`{"authorization_url": "..."}` em JSON em vez de um redirect HTTP. O botão
continuava fazendo `window.location.href` direto na URL do endpoint, o que
resultava numa navegação para uma página em branco mostrando o JSON cru, em
vez de levar o usuário ao X.

**Solução:** `services/twitterAccounts.ts::getTwitterOAuthLoginUrl()` agora
faz uma chamada autenticada via Axios (o interceptor já anexa o Bearer
token), lê `authorization_url` da resposta, e só então
`ConnectAccountButton.tsx` navega o navegador para essa URL. Adicionado
estado de carregamento no botão e tratamento de erro (toast) caso a chamada
falhe.

**Arquivos:** `services/twitterAccounts.ts`, `components/accounts/ConnectAccountButton.tsx`.

## 2. `GET /auth/me` — fim dos workarounds de identidade do usuário

**Problema:** sem esse endpoint, o frontend usava o e-mail digitado no
formulário de login e uma sonda indireta (`GET /admin/plans`, observando
200 vs. 401/403) para inferir o papel do usuário.

**Solução:**
- `services/auth.ts::getCurrentUser()` chama `GET /auth/me`.
- Novo hook `hooks/useCurrentUser.ts` (TanStack Query) é a única fonte de
  verdade do perfil do usuário logado — dedupe automático entre todos os
  componentes que o usam (Sidebar, UserMenu, Settings, AdminRoute).
- `hooks/useAuth.ts::useSession()` agora deriva `user`, `userId` e `isAdmin`
  diretamente da resposta real de `/auth/me`, sem sondas.
- `stores/authStore.ts` simplificado: guarda só os tokens (dados de perfil
  saíram do Zustand, evitando duas fontes de verdade divergentes).
- `hooks/useAdminProbe.ts` removido (obsoleto).
- `UserMenu.tsx` agora mostra o **nome real** do usuário (com o e-mail como
  subtítulo), não mais o e-mail digitado no login.
- `SettingsPage.tsx` mostra nome, e-mail e ID vindos do backend, com
  skeleton de carregamento.

**Arquivos:** `services/auth.ts`, `hooks/useCurrentUser.ts` (novo),
`hooks/useAuth.ts`, `stores/authStore.ts`, `routes/AdminRoute.tsx`,
`layouts/DashboardLayout.tsx`, `components/layout/UserMenu.tsx`,
`pages/SettingsPage.tsx`. Removido: `hooks/useAdminProbe.ts`.

## 3. Assinatura por usuário — fim do campo de ID manual

**Problema:** `SubscriptionActionsDialog` exigia que o admin digitasse o
`subscription_id` manualmente, já que não havia endpoint para descobri-lo.

**Solução:** o diálogo agora recebe `userId`/`userName` (em vez de um id
opcional) e busca a assinatura automaticamente ao abrir, via
`GET /admin/users/{id}/subscription`. Também passou a **exibir** os dados
da assinatura (status, data de expiração, posts usados, posts extras) antes
de qualquer ação — melhoria em relação ao que existia antes, que era só um
formulário cego. As mutações (renovar/bloquear/expirar/créditos extras)
agora invalidam essa consulta automaticamente após cada ação, mantendo os
dados exibidos sempre atualizados.

**Arquivos:** `services/subscriptions.ts`, `hooks/useAdminSubscriptions.ts`,
`components/admin/SubscriptionActionsDialog.tsx`, `pages/AdminUsersPage.tsx`.

## 4. Detalhamento por conta no histórico de posts

**Problema:** um post com múltiplas contas mostrava só o status agregado —
impossível saber qual conta específica falhou ou por quê.

**Solução:** `types/post.ts::Post` ganhou o campo `accounts` (já retornado
pelo backend em `GET /posts`/`GET /posts/{id}`). Novo componente
`components/posts/PostAccountsBreakdown.tsx` mostra um selo por conta
(ícone de sucesso/falha/pendente + `@usuário`), com tooltip exibindo a
mensagem de erro exata quando a conta falhou. Só aparece quando o post tem
mais de uma conta (com uma única conta, o status agregado já basta).

**Arquivos:** `types/post.ts`, `components/posts/PostAccountsBreakdown.tsx` (novo),
`components/posts/PostRow.tsx`.

## 5. Data de agendamento via backend, não mais `localStorage`

**Problema:** a data exata de um agendamento só ficava disponível no mesmo
navegador em que foi criado (cache em `localStorage`), já que não havia
endpoint para recuperá-la depois.

**Solução:** `GET /posts/{id}/schedule` agora existe. Novo hook
`useScheduledPostDetails` (usando `useQueries` do TanStack Query) busca a
data de cada post agendado diretamente do backend. `lib/scheduledPostCache.ts`
foi removido (dead code) e o aviso permanente sobre a limitação saiu da
tela de Agendamentos, já que a limitação não existe mais.

**Arquivos:** `services/posts.ts`, `hooks/usePosts.ts`,
`pages/ScheduledPage.tsx`. Removido: `lib/scheduledPostCache.ts`.

## 6. Limpeza de código morto

Removidos dois arquivos órfãos que não eram importados por nada em lugar
nenhum (sobras de uma versão anterior que voltaram a aparecer no envio):
`components/StatusCard.tsx` e `components/IntelligentPublicationPreviewModal.tsx`
(a versão antiga, na raiz de `components/` — a versão em uso continua em
`components/intelligent-publication/`).

## Validação

- Todas as importações (`@/...`) verificadas contra os arquivos reais após
  as mudanças.
- Balanceamento de chaves/parênteses/colchetes conferido em todo o código.
- Nenhuma referência restante a `probeIsAdmin`, `useAdminProbe`,
  `scheduledPostCache` ou `buildTwitterOAuthLoginUrl` (todos substituídos).
- Como no envio anterior, não foi possível rodar `npm install`/`tsc`/build
  real neste ambiente (sem acesso à rede) — recomenda-se `npm install &&
  npm run build` como validação final antes de testar manualmente.

---

# CHANGELOG — Frontend do XHub

Este documento descreve a implementação completa do frontend do XHub a partir do
esqueleto existente (que continha apenas uma página de health-check). Todo o
frontend foi construído consumindo exclusivamente as APIs já existentes no
backend — nenhum arquivo do backend foi alterado.

> **Nota sobre o `.continue`**: o pedido mencionava reler a pasta `.continue`.
> Assim como em uma rodada anterior deste projeto, essa pasta não está presente
> no arquivo enviado (o `CHANGELOG.md` da raiz do projeto referencia sua
> criação, mas ela não veio no zip). O frontend foi construído usando o código
> real do backend como fonte da verdade, conforme instruído.

---

## Stack instalada

React 19 · TypeScript · Vite 6 · React Router 7 · TanStack Query v5 · Tailwind
CSS 3 · shadcn/ui (componentes escritos à mão, sem CLI — sem acesso à rede
neste ambiente para `npx shadcn add`, então cada primitivo foi implementado
seguindo exatamente o código-fonte/padrão oficial do shadcn) · React Hook Form
+ Zod · Lucide Icons · Framer Motion · Zustand (estado de autenticação).

---

## Identidade visual

- **Paleta**: preto azulado profundo (`--background: 220 13% 4%`) como base,
  um único azul de destaque (`--primary: 221 92% 60%`) usado com moderação —
  ações primárias, estados ativos, e o motivo visual da Publicação
  Inteligente. Sucesso/aviso/erro em tons dessaturados compatíveis com o tema
  escuro.
- **Tipografia**: Inter para texto de interface (mantida do esqueleto
  original), **Instrument Sans** para títulos/display (carregada via Google
  Fonts em `index.html`), **JetBrains Mono** para dados técnicos (IDs,
  timestamps, contadores de caracteres).
- **Motivo de marca**: um nó se ramificando em três (`components/common/Logo.tsx`)
  — representa literalmente o que a Publicação Inteligente faz (um texto
  original se tornando várias variações). Reaproveitado como animação de
  carregamento no modal de preview (`VariationLoadingState.tsx`).
- **Espaçamento generoso, cantos suaves (`--radius: 0.75rem`), cards com
  bordas sutis** — conforme solicitado.

---

## Estrutura de pastas

```
src/
├── components/
│   ├── ui/                    # primitivos shadcn/ui (button, card, dialog, ...)
│   ├── common/                # Logo, PageHeader, EmptyState, ConfirmDialog, ...
│   ├── layout/                # Sidebar, UserMenu
│   ├── accounts/               # componentes da tela de Contas do X
│   ├── posts/                  # componentes de posts/composer/agendamento
│   ├── intelligent-publication/ # modal de preview e peças da Publicação Inteligente
│   ├── dashboard/               # StatCard
│   └── admin/                   # diálogos administrativos
├── pages/                      # uma página por rota
├── layouts/                    # AuthLayout, DashboardLayout
├── routes/                     # ProtectedRoute, AdminRoute (guards)
├── hooks/                      # um hook por domínio (TanStack Query)
├── services/                   # um arquivo por domínio (chamadas Axios)
├── stores/                     # authStore (Zustand + persist)
├── types/                      # espelham exatamente os schemas Pydantic
└── lib/                        # utils, format, scheduledPostCache
```

---

## Telas implementadas

| Tela | Rota | Descrição |
|---|---|---|
| Login | `/login` | Formulário com React Hook Form + Zod. |
| Dashboard | `/` | Estatísticas (contas, publicados, agendados, falhados), atividade recente, status do sistema. |
| Contas do X | `/accounts` | Lista de contas conectadas, conectar/desconectar. |
| Novo post | `/posts/new` | Composer completo com o fluxo de Publicação Inteligente. |
| Histórico | `/posts` | Lista com abas por status, publicar/excluir. |
| Agendamentos | `/scheduled` | Posts com status `scheduled`, cancelar agendamento. |
| Configurações | `/settings` | Dados da sessão, logout. |
| Usuários (admin) | `/admin/users` | Criar usuário (com plano/assinatura), bloquear/desbloquear, trocar papel, ações de assinatura. |
| Planos (admin) | `/admin/plans` | Catálogo de planos, sincronizar, editar preço/limites. |

---

## Fluxo da Publicação Inteligente (destaque do produto)

Implementado exatamente conforme os 7 passos pedidos, em `pages/NewPostPage.tsx`:

1. **Escrever o texto** — textarea com contador de caracteres estilo X.
2. **Selecionar as contas** — `AccountSelector`, grid multi-seleção.
3. **Gerar preview** — botão dispara `POST /intelligent-publication/preview`
   via `useIntelligentPublicationPreview` (mutation).
4. **Visualizar variações** — `IntelligentPublicationPreviewModal` mostra o
   texto original, o aviso de recomendação (2–4 contas), e um card animado
   por conta com a variação sugerida.
5. **Editar manualmente** — cada card tem um `Textarea` controlado; edições
   são revalidadas no cliente (vazio/duplicado/limite) e, ao confirmar,
   revalidadas de novo no backend (`PostService.create_post`).
6. **Confirmar** — `POST /posts` é chamado com `rendered_texts` (mapa
   `twitter_account_id -> texto final`), reaproveitando o endpoint de
   criação de posts já existente em vez de duplicar lógica.
7. **Publicar imediatamente ou agendar** — `PublishOrScheduleDialog` chama
   `POST /posts/{id}/publish` ou `POST /posts/{id}/schedule`.

Estados tratados fielmente ao roadmap oficial:
- **1 conta**: nunca chama a Groq, publica o texto original.
- **2–4 contas**: variação opcional, ativada por padrão (`Switch`); se a Groq
  falhar, o backend já faz fallback para o texto original — o frontend só
  exibe o aviso correspondente.
- **5+ contas**: variação obrigatória; o botão de confirmar fica bloqueado
  se houver texto vazio ou duplicado entre as contas; erro de indisponibilidade
  da Groq mostra alerta com "Tentar novamente" / "Salvar como rascunho".

---

## Decisões arquiteturais

### Estado de autenticação: Zustand + persist, não Context
Optado por Zustand (nova dependência, pequena e amplamente usada) em vez de
Context API pura para o estado de sessão, porque evita re-renders em cascata
e é lido tanto por componentes React quanto pelo interceptor do Axios (fora
da árvore de componentes) — algo que Context não permite sem gambiarras.

### Refresh token automático no Axios
`services/api.ts` implementa um interceptor de resposta que, em qualquer
`401` (exceto nas próprias rotas de auth), tenta `POST /auth/refresh`
automaticamente uma única vez, deduplicando chamadas concorrentes de refresh,
e só desloga o usuário se o refresh também falhar.

### Cache client-side para `scheduled_for`
O backend não expõe nenhum `GET` para recuperar os detalhes de um
agendamento após criado — apenas a resposta de `POST /posts/{id}/schedule`
traz essa data. `lib/scheduledPostCache.ts` guarda esse valor no
`localStorage` no momento em que é conhecido, como cache de exibição
best-effort (documentado, nunca inventa dado).

### Componentes shadcn/ui escritos à mão
Sem acesso à rede neste ambiente para rodar `npx shadcn add`, cada primitivo
(`button`, `dialog`, `select`, etc.) foi implementado manualmente seguindo
fielmente o código-fonte oficial do shadcn/ui sobre Radix UI — mesma API,
mesmas convenções (`cva`, `cn`, `forwardRef`), para que `npx shadcn add` (ou
atualizações futuras) continue funcionando normalmente sobre esta base.

### `datetime-local` nativo em vez de um calendário dedicado
`components/common/DateTimePicker.tsx` usa `<input type="datetime-local">`
estilizado, em vez de uma biblioteca de calendário — suficiente para o único
uso (agendar publicação) e evita uma dependência não solicitada.

---

## Limitações conhecidas (backend não foi alterado)

Estas lacunas já existiam no backend antes deste trabalho e são contornadas
da forma mais honesta possível no frontend, sempre documentadas no código:

1. **Não existe `GET /me`.** O login (`POST /auth/login`) devolve apenas
   tokens — nome, e-mail e papel do usuário nunca são retornados pela API.
   Contorno: `email` é guardado a partir do que o usuário digitou no
   formulário de login; `role` é descoberto por uma sonda best-effort
   (`services/auth.ts::probeIsAdmin`, chama `GET /admin/plans` e observa
   200 vs. 401/403). Correção ideal: adicionar `GET /me`.

2. **`GET /oauth/x/login` exige Bearer token E responde com redirect HTTP.**
   Uma navegação de página inteira (necessária para chegar à tela de login
   do X) não envia headers customizados, então essa combinação não é
   satisfazível por um SPA que guarda o JWT fora de cookies. O botão
   "Conectar conta do X" (`components/accounts/ConnectAccountButton.tsx`)
   faz a navegação correta do ponto de vista de produto, mas ela só
   funcionará de fato depois de um ajuste pequeno no backend — o ideal é
   esse endpoint devolver `{ "authorization_url": "..." }` como JSON,
   deixando o frontend fazer `window.location.href` com o valor retornado.

3. **Não existe nenhum `GET` para assinaturas** (nem lista, nem por usuário).
   `components/admin/SubscriptionActionsDialog.tsx` funciona apenas com um
   `subscription_id` informado manualmente pelo administrador. Correção
   ideal: `GET /admin/subscriptions` e/ou `GET /admin/users/{id}/subscription`.

4. **`GET /posts` não retorna o detalhamento por conta** (`PostAccount`) —
   não há como mostrar, no histórico, quais contas especificamente falharam
   ou tiveram sucesso dentro de um post com múltiplas contas, apenas o
   status agregado do post. Correção ideal: incluir a lista de
   `PostAccount` (ou um resumo) na resposta de `GET /posts`/`GET /posts/{id}`.

5. **`scheduled_for` não é recuperável após a criação do agendamento** (ver
   decisão arquitetural acima sobre o cache local).

Nenhuma dessas limitações impede o uso do produto — cada uma foi tratada com
um fallback claro e visível para o usuário, nunca com um dado inventado ou
uma falha silenciosa.

---

## Revisão final

- Todas as importações (`@/...`) foram verificadas contra os arquivos reais.
- Todos os tipos TypeScript foram conferidos campo a campo contra os schemas
  Pydantic reais do backend (`UserResponse`, `PlanResponse`,
  `SubscriptionResponse`, `PostResponse`, `ScheduledPostResponse`,
  `TwitterAccountResponse`, `TokenResponse`, os schemas de
  `intelligent_publication.py`).
- Ícone `Twitter` do Lucide (removido de versões recentes da biblioteca, além
  de representar a marca antiga) substituído por `AtSign` em todos os pontos
  de uso.
- `ConfirmDialog` corrigido para suportar uso 100% controlado (sem
  `DialogTrigger`), evitando abrir o diálogo ao clicar em qualquer parte do
  card de conta em `AccountsPage`.
- Sonda de papel do usuário (`isAdmin`) movida para rodar assim que o layout
  autenticado monta, não apenas ao entrar em uma rota `/admin/*` — evita a
  seção "Administração" do menu lateral ficar escondida indevidamente após
  um refresh de página.
- Nenhum código morto do esqueleto original permanece (`StatusCard.tsx`
  antigo removido; `useHealthCheck`/`types/health.ts` foram mantidos e
  reaproveitados no Dashboard, evitando duplicação).
- Não foi possível rodar `npm install`/`tsc`/build real neste ambiente (sem
  acesso à rede para baixar pacotes) — a revisão foi feita por leitura
  completa de cada arquivo, checagem de balanceamento de chaves/parênteses
  em todo o código, e conferência campo a campo contra o backend real.
  Recomenda-se rodar `npm install && npm run build` localmente como
  validação final antes de deploy.
