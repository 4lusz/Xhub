# CHANGELOG — Auditoria de segurança completa pré-commit (JWT + rate limiting)

Detalhe completo em `CHANGELOG.md` (raiz) e `docs/AUDITORIA_SEGURANCA.md`.

- **Migration `d7e8f9a0b1c2`** — tabela `revoked_access_tokens` (`jti`
  PK, `expires_at`, `revoked_at`).
- **`app/models/revoked_access_token.py`** (novo).
- **`app/repositories/revoked_access_token_repository.py`** (novo) —
  `is_revoked`, `revoke` (idempotente), `delete_expired`.
- **`app/auth/jwt.py`** — todo access token ganhou claim `jti` (UUID).
- **`app/services/auth_service.py`** — `revoke_access_token` (decodifica,
  extrai `jti`/`exp`, revoga e limpa entradas expiradas).
- **`app/auth/dependencies.py`** — `_resolve_authenticated_user` rejeita
  qualquer token com `jti` revogado; `oauth2_scheme_optional` (nunca
  falha sozinho, usado só no logout).
- **`app/routes/auth.py`** — `POST /auth/logout` também revoga o
  access token em uso, além do refresh token.
- **`app/middleware/rate_limit.py`** — segunda dimensão de limite por
  usuário autenticado (JWT `sub`, sem verificar assinatura) ou alvo
  submetido (e-mail no login, token no refresh/2FA), independente do
  IP; `AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS` (novo, padrão 5) para
  login/refresh/2FA.

Validado: `pytest` (14/14, 8 novos: `test_rate_limit.py`,
`test_security_headers.py`, 2 em `test_routes_auth.py`, 2 em
`test_routes_post.py`), requisições HTTP reais confirmando o ciclo
completo login → logout → token rejeitado (401) → refresh token
também rejeitado.

# CHANGELOG — Separação Fluxo 1/Fluxo 2 de composição de post

Detalhe completo em `CHANGELOG.md` (raiz), `docs/ROADMAP_COMPOSICAO_POST.md`
e `docs/AUDITORIA_SEGURANCA.md`.

- **Migration `c6d7e8f9a0b1`** — `posts.composition_mode` (enum nativo
  `post_composition_mode`, default `SHARED` para linhas existentes),
  `posts.text` passa a nullable, `post_media.post_account_id` (FK
  nullable para `post_accounts.id`).
- **`app/models/enums.py`** — `PostCompositionMode`. Não duplicado em
  `app.domain.enums` (diferente de `UserRole`/`SubscriptionStatus`) —
  as funções de domínio usam tipos primitivos.
- **`app/domain/post_composition.py`** (novo) — `find_accounts_missing_independent_text`,
  função pura.
- **`app/repositories/post_media_repository.py`** —
  `list_for_post_account` (mídia compartilhada + individual de uma
  conta, window function); `attach_to_post` ganhou `post_account_id`
  opcional.
- **`app/services/post_service.py`** — `create_post` bifurca por
  `composition_mode` (texto principal obrigatório/proibido, texto por
  conta obrigatório/opcional, mídia compartilhada e/ou individual via
  `_validate_and_load_account_media`, que rejeita reuso da mesma mídia
  em contas diferentes); `publish_post` pula a checagem de variação
  obrigatória de 5+ contas fora do modo SHARED e calcula o custo por
  conta a partir do texto EFETIVO de cada uma (antes, uma única vez
  sobre `Post.text`).
- **`app/routes/post.py`** — `CreatePostRequest` ganhou
  `composition_mode`, `text` opcional, `account_media_ids`;
  `PostResponse`/`PostAccountResponse` expõem `composition_mode` e
  `rendered_text`; `PostMediaResponse` expõe `post_account_id`.

Validado: `pytest` (6/6, sem regressão), script descartável com 17
checagens (criação nos dois modos, texto faltando/proibido, mídia
compartilhada vs. individual, reuso de mídia entre contas rejeitado,
custo por texto com/sem link) e requisições HTTP reais contra o
backend local — tudo removido/limpo após validar.

# CHANGELOG — Coleta decrescente de métricas por idade do post

Detalhe completo em `CHANGELOG.md` (raiz) e `docs/ROADMAP_METRICAS.md`.

- **`app/config/settings.py`** — `METRICS_POST_RECENT_WINDOW_HOURS`
  (72), `METRICS_POST_RECENT_INTERVAL_HOURS` (12),
  `METRICS_POST_AGING_WINDOW_DAYS` (7), `METRICS_POST_AGING_INTERVAL_HOURS`
  (24), `METRICS_ACCOUNT_INACTIVE_AFTER_DAYS` (30),
  `METRICS_ACCOUNT_INACTIVE_COLLECTION_INTERVAL_HOURS` (168).
- **`app/domain/metrics.py`** — `should_collect_post_metrics` (coleta
  decrescente por idade, com "snapshot final" único depois da janela de
  aging) e `should_collect_account_metrics` (throttle de seguidores em
  conta inativa, nunca para por completo) — funções puras, sem I/O.
- **`app/repositories/post_metric_snapshot_repository.py`** —
  `get_latest_by_post_accounts` (bulk, window function), evita N+1 ao
  decidir por post se já passou o intervalo mínimo.
- **`app/services/metrics_service.py`** — `_collect_for_account` agora
  filtra por essas regras antes de chamar a API do X, tanto para
  seguidores quanto para métricas de post.

Validado: suíte `pytest` (6/6, sem regressão) + script descartável
cobrindo os limites de cada janela (72h, 7 dias, snapshot final já
tirado vs. pendente, conta inativa com/sem coleta prévia) — removido
após validar.

# CHANGELOG — Segundo fator de login (pergunta de segurança)

Detalhe completo em `CHANGELOG.md` (raiz) e `docs/AUDITORIA_SEGURANCA.md`.

- **Migration `b5c6d7e8f9a0`** — colunas `security_question`/
  `security_answer_hash` (nullable) em `users`.
- **`app/models/user.py`** — os dois campos novos.
- **`app/domain/security_answer.py`** (novo) — `normalize_security_answer`,
  função pura (strip + colapso de espaços + casefold), sem I/O.
- **`app/services/auth_service.py`** — `requires_second_factor`,
  `issue_pending_2fa_token` (JWT de 5 min, claim `stage: pending_2fa`),
  `verify_security_answer`.
- **`app/auth/dependencies.py`** — `_resolve_authenticated_user` rejeita
  explicitamente qualquer token com `stage == "pending_2fa"` — sem essa
  checagem o token pendente seria um bypass de autenticação completo.
- **`app/services/user_service.py`** — `set_security_question`/
  `clear_security_question`.
- **`app/routes/auth.py`** — `login` retorna `TokenResponse |
  SecondFactorRequiredResponse`; novas rotas
  `POST /auth/verify-security-answer` (pública, rate-limited),
  `POST`/`DELETE /auth/security-question` (admin-only).
- **`app/middleware/rate_limit.py`** — `/auth/verify-security-answer`
  adicionada aos paths com rate limit.

Validado: suíte `pytest` (6/6, incluindo fixtures atualizadas em
`conftest.py`/`test_routes_auth.py`) e teste ao vivo via curl contra o
backend local (resposta errada rejeitada, resposta certa com
diferença de maiúsculas/espaços aceita via normalização, token
pendente confirmado rejeitado como Bearer normal).

# CHANGELOG — Atualização de fastapi/starlette (CVEs corrigidos)

A auditoria de segurança (`docs/AUDITORIA_SEGURANCA.md`) tinha deixado
a atualização de `fastapi`/`starlette` como recomendação para uma etapa
dedicada, por ser uma mudança de framework de maior superfície (toda
rota/middleware/serialização) — não executada às pressas dentro da
própria auditoria. Executada agora, a pedido explícito do usuário, com
autorização para corrigir qualquer regressão encontrada.

- **`requirements.txt`** — `fastapi` 0.115.6 → 0.136.0. Investigado com
  `pip install --dry-run` antes de aplicar: essa versão já resolve
  `starlette` para 1.3.1 (a mais recente disponível), eliminando os 7
  CVEs conhecidos que a versão anterior (`starlette==0.41.3`, fixada
  transitivamente por `fastapi==0.115.6`) carregava. Escolhida 0.136.0
  em vez da mais recente (0.139.2) porque ambas resolvem para a mesma
  versão de `starlette` — sem diferença de segurança em ir além, só
  risco adicional de regressão.

Validado com regressão completa (salto de 24 versões menores do
FastAPI + mudança de versionamento maior `0.x → 1.x` do Starlette
justificam ir além do `pytest`):
- `docker compose build backend` sem cache — build limpo.
- `pytest` 6/6, sem regressão funcional (nova
  `StarletteDeprecationWarning` sobre `httpx` no `TestClient` — apenas
  informativa, sobre uma futura descontinuação em ferramenta de teste,
  sem efeito em código de produção).
- Headers de segurança, CORS (preflight), login/JWT, rate limiting em
  rota dinâmica (`/posts/{id}/publish`), limite de corpo de requisição
  (413 em payload de 2MB + multipart de mídia isento), handler global
  de exceção (404 padrão sem vazamento) e redirect do callback OAuth do
  X — todos revalidados ao vivo, comportamento idêntico ao anterior.
- `pip-audit`: 34 → 9 vulnerabilidades conhecidas restantes, todas já
  documentadas individualmente em `docs/AUDITORIA_SEGURANCA.md` como
  risco aceito (`ecdsa`/`pyasn1` — caminho RSA/EC nunca exercitado por
  este projeto, que usa só HS256; `pip`/`pytest` — fora da superfície
  de ataque de produção).

# CHANGELOG — Correção: redirect do OAuth do X após site de marketing

Bug real encontrado numa auditoria de segurança pedida explicitamente
pelo usuário, logo após a construção do site público de marketing (ver
`frontend/CHANGELOG.md`). Detalhe completo em `CHANGELOG.md` (raiz).

**Causa raiz:** `app/routes/oauth.py::_frontend_redirect` redirecionava
`GET /oauth/x/callback` para a raiz de `FRONTEND_URL` -- correto
enquanto a raiz era a tela autenticada de contas conectadas, mas a raiz
virou a landing page pública de marketing. O toast de sucesso/erro da
conexão (`useOAuthCallbackFeedback`, montado só no layout autenticado)
deixaria de aparecer para o usuário depois de conectar uma conta.

**Correção:** redireciona especificamente para `FRONTEND_URL/accounts`
(tela onde a conexão é iniciada, dentro do layout autenticado que
captura os parâmetros de query).

Validado: `pytest` sem regressão (6/6), redirect testado ao vivo
(`GET /oauth/x/callback?state=...&error=...` retorna `307` com
`Location` apontando para `/accounts`, não mais para a raiz).

# CHANGELOG — Métricas de desempenho ("Resultados")

Nova funcionalidade pedida explicitamente pelo usuário. Detalhe completo
em `docs/ROADMAP_METRICAS.md`.

- **`app/domain/metrics.py`** (novo) — funções puras: `compute_percent_change`
  (variação percentual entre períodos) e `detect_reach_anomaly` (compara
  o alcance recente de uma conta contra o histórico DELA MESMA — nunca
  entre contas diferentes).
- **`app/models/account_metric_snapshot.py`/`post_metric_snapshot.py`**
  (novos) — duas tabelas append-only (mesmo princípio de `AuditLog`).
  `PostMetricSnapshot.twitter_account_id` denormalizado a partir de
  `PostAccount` para evitar JOIN na consulta de portfólio.
- **`alembic/versions/a4b5c6d7e8f9_create_metric_snapshots_tables.py`**
  (novo) — cria as duas tabelas.
- **`app/oauth/oauth_client.py`** — dois métodos novos:
  `get_account_metrics` (seguidores) e `get_tweet_metrics` (impressões/
  curtidas/respostas/republicações/citações, até 100 tweets da MESMA
  conta por chamada). `impression_count` (`organic_metrics`, exige
  contexto de usuário) nunca levanta exceção só por não estar
  autorizado para o tier/app atual — volta `None` nesse caso.
  `_raise_for_media_error` renomeado para `_raise_for_x_api_error`
  (sempre foi genérico, agora reaproveitado por 3 métodos em vez de 1).
- **`app/services/metrics_service.py`** (novo, `MetricsService`) —
  coleta (`collect_all`, chamada só pelo scheduler, commit/rollback por
  conta) e consulta (portfólio/conta/post, sempre escopada ao usuário
  autenticado, mesmo padrão de IDOR do resto do projeto).
- **`app/scheduler.py`** — novo job `collect_account_and_post_metrics`
  no MESMO `BackgroundScheduler` já existente (nunca um worker/broker
  novo), intervalo próprio (`METRICS_COLLECTION_INTERVAL_SECONDS`,
  padrão 6h).
- **`app/routes/metrics.py`** + **`app/schemas/metrics.py`** (novos) —
  `GET /metrics/accounts`, `GET /metrics/accounts/{id}`,
  `GET /metrics/post-accounts/{id}`. Somente leitura.
- **`app/config/settings.py`** — `METRICS_*` (habilitar/desabilitar,
  intervalo de coleta, janela de retenção de posts, parâmetros de
  detecção de anomalia).
- **`app/repositories/post_account_repository.py`** — dois métodos
  novos: `list_published_within_by_account` (janela de coleta) e
  `list_published_by_account` (melhores posts).

Validado: script Python descartável com 20 asserções (funções de
domínio, coleta end-to-end com dublê de `XOAuthClient`, consulta de
portfólio, bloqueio append-only, IDOR) — 20/20, criado/executado/apagado.
`pytest` 6/6 sem regressão. Migration real aplicada
(`f6a7b8c9d0e1 → a4b5c6d7e8f9`). Rotas testadas ao vivo: portfólio vazio
sem erro, 404 para conta/post de outro usuário, 401 sem token, headers
de segurança intactos.

# CHANGELOG — Correção: endpoint STATUS de upload de mídia (404 real)

Bug real encontrado na primeira publicação de vídeo com uma conta do X
reconectada (créditos de mídia disponíveis na conta do usuário) —
`PostAccount.error_message = "Upload de midia (STATUS): 404 - sem corpo
de resposta"`. Detalhe completo em `docs/ROADMAP_MEDIA.md`.

**Causa raiz:** `XOAuthClient._wait_for_media_processing` assumia que o
passo `STATUS` do upload chunked de mídia seguiria o mesmo padrão de
caminho dedicado das demais etapas (`GET /2/media/upload/{id}/status`)
— suposição nunca antes testada contra a API real (documentado
explicitamente no próprio código como pendente de validação). A
documentação oficial do X
(`docs.x.com/x-api/media/quickstart/media-upload-chunked`) confirma que
STATUS é a única etapa que NÃO tem caminho dedicado no v2: continua no
padrão legado v1.1, via query string no endpoint base
(`GET /2/media/upload?command=STATUS&media_id={id}`).

**Correção:** `app/oauth/oauth_client.py` — `_media_request` ganhou um
parâmetro `query_params` opcional; `_wait_for_media_processing` passou
a chamar `GET /2/media/upload?command=STATUS&media_id={id}` em vez do
caminho dedicado inexistente. `initialize`/`append`/`finalize`
permanecem inalterados (já confirmados corretos em teste real anterior).

Validado: `pytest` sem regressão (6/6), `import app.main` limpo,
construção da URL final confirmada byte a byte contra o formato exato
da documentação oficial antes do rebuild do container.

# CHANGELOG — Auditoria completa de segurança

Última auditoria do projeto antes de produção. Relatório técnico
completo, metodologia e lista de validações em
`docs/AUDITORIA_SEGURANCA.md`. 5 vulnerabilidades reais corrigidas
(nenhuma Crítica), seguindo exatamente a arquitetura existente (nenhuma
infraestrutura nova, nenhuma funcionalidade de produto):

- **`app/middleware/security_headers.py`** (novo) —
  `SecurityHeadersMiddleware`, mesmo padrão de
  `RequestContextMiddleware`/`RateLimitMiddleware`. Aplica
  `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
  `Referrer-Policy: no-referrer`, `Permissions-Policy` e
  `Strict-Transport-Security` em toda resposta — antes, nenhum header de
  segurança era definido (clickjacking possível, sem defesa em
  profundidade contra XSS futuro).
- **`app/middleware/rate_limit.py`** — cobertura estendida de
  `/auth/login` (único endpoint protegido antes) para também incluir
  `/auth/refresh`, `/intelligent-publication/preview` (custo real por
  chamada à Groq), `/media/upload` (até 512MB por arquivo, sem cota),
  `/oauth/x/login`, e `/posts/{id}/publish`/`/posts/{id}/schedule`
  (caminhos dinâmicos, casados por regex de UUID). Chave de rate limit
  passou a incluir o método HTTP, para que leitura e escrita no mesmo
  caminho nunca compartilhem orçamento. `POST /admin/users` e
  auto-registro deliberadamente fora do escopo (exigem admin
  autenticado / não existem, respectivamente — fora do modelo de ameaça
  "atacante com acesso apenas à API pública").
- **`app/domain/plans.py`** — nova constante
  `MAX_ACCOUNTS_ACROSS_PLANS` (maior `max_accounts` do catálogo oficial,
  hoje 100). Aplicada como `max_length` em
  `CreatePostRequest.twitter_account_ids`
  (`app/routes/post.py`) e
  `IntelligentPublicationPreviewRequest.twitter_account_ids`
  (`app/schemas/intelligent_publication.py`) — antes, uma lista sem
  limite de UUIDs forçava uma consulta síncrona ao banco por item,
  antes de qualquer validação de posse (DoS de payload).
- **`app/middleware/body_size_limit.py`** (novo) —
  `BodySizeLimitMiddleware`, rejeita (413) requisições não-multipart com
  `Content-Length` acima de 1 MiB antes de qualquer leitura de corpo.
  Rotas multipart (upload de mídia) explicitamente isentas — já
  protegidas em streaming por `app.core.media_storage.save_upload`.
- **`app/services/auth_service.py`** — `AuthService.authenticate` agora
  verifica um hash bcrypt "isca" mesmo quando o e-mail não existe,
  igualando o tempo de resposta ao caso de senha incorreta — antes, a
  ausência de e-mail pulava a verificação bcrypt (lenta por design),
  criando um side-channel de timing que permitia enumerar e-mails
  cadastrados sem depender do conteúdo da mensagem de erro (que já era
  idêntica nos dois casos).
- **`requirements.txt`** — `cryptography` 43.0.3→48.0.1, `python-jose`
  3.3.0→3.4.0, `python-multipart` 0.0.20→0.0.32, `python-dotenv`
  1.0.1→1.2.2 (CVEs conhecidos corrigidos upstream). `ecdsa`/`pyasn1`
  (transitivos, usados só pelo caminho RSA/EC do `python-jose` — esta
  aplicação usa exclusivamente HS256) e `starlette`/`fastapi`
  permanecem com CVEs conhecidos, documentados individualmente em
  `docs/AUDITORIA_SEGURANCA.md` como risco aceito ou recomendação para
  a próxima etapa (mudança de framework de maior superfície).

Validado: `docker compose build backend` sem cache (duas vezes),
`pytest` 6/6 sem regressão em cada rebuild, roundtrip real de
`Fernet`/JWT nas novas versões, simulação de flood ao vivo (40
requisições) confirmando `429` em cada endpoint estendido, `413` real
em corpo de 2MB, `422` real em lista de 150 UUIDs, `pip-audit` (34→18
vulnerabilidades conhecidas, restantes justificadas individualmente).

# CHANGELOG — Custo de publicação por link (15 créditos/conta)

Implementação de regra de negócio explicitamente pedida pelo usuário:
post com link no texto consome **15 créditos por conta publicada**;
qualquer outro post (texto simples ou com mídia, sem link) continua
consumindo **1 crédito por conta**, comportamento já existente. Mídia
anexada nunca altera o custo. Detalhe completo em
`docs/ROADMAP_CUSTO_LINK.md`.

- `app/domain/publication_cost.py` — reescrito. O código antigo
  (`PublicationContentType`/`PublicationCostPolicy`, classificação
  mutuamente exclusiva TEXT/IMAGE/VIDEO/LINK) nunca esteve conectado ao
  fluxo real e não refletia a regra correta (mídia e link não são
  categorias mutuamente exclusivas). Substituído por
  `post_text_has_link(text)`/`credits_per_account_for_post(text)` —
  reaproveita a mesma detecção de URL já usada pela Publicação
  Inteligente (`app.domain.content_invariants.extract_invariants`).
  `PublicationContentType` removido de `app/domain/enums.py` por ficar
  sem nenhum uso.
- `app/services/post_service.py` (`PostService.publish_post`) — calcula
  `credits_per_account_for_post(post.text)` uma única vez por post,
  logo antes da validação de saldo; usado tanto em
  `SubscriptionService.ensure_can_publish(required_posts=len(accounts_to_publish) * credits_per_account)`
  (validação ANTES de qualquer chamada ao X) quanto em
  `SubscriptionService.consume_posts(subscription.id, credits_per_account)`
  (consumo por conta publicada com sucesso). Nenhuma outra parte do
  fluxo (idempotência, Jitter, mídia, Publicação Inteligente, commit
  por conta) foi alterada.

Decisão técnica: a classificação usa sempre `Post.text` (o texto
original), nunca `PostAccount.rendered_text` individualmente — correto
mesmo com Publicação Inteligente, já que toda variação é obrigada a
preservar exatamente os mesmos links do original
(`preserves_invariants` descarta qualquer variação que altere links).

Validado: `python -c "import app.main"` limpo; `pytest` sem regressão
(6 passaram, 0 falharam); script Python descartável (removido após a
validação, com dublê de `XOAuthClient`, nunca a API real do X) — post
sem link com 2 contas consome exatamente 2 créditos; post com link e 2
contas consome exatamente 30 créditos; saldo suficiente para o custo
antigo mas insuficiente para o novo é bloqueado antes de qualquer
chamada ao X; custo independe de mídia anexada.

# CHANGELOG — Auditoria funcional completa

Validação de ponta a ponta de todo o backend antes da auditoria de
segurança final. Relatório técnico completo em
`docs/AUDITORIA_FUNCIONAL.md`. Problemas reais corrigidos nesta etapa
(causa raiz, sem funcionalidade nova):

- **`AuthService.authenticate`** (`app/services/auth_service.py`): não
  checava `user.is_blocked` — um usuário bloqueado conseguia completar
  `POST /auth/login` normalmente e receber tokens válidos, contrariando
  a própria regra documentada em
  `app.domain.policies.ensure_user_not_blocked`. Corrigido para
  levantar `ForbiddenException("Usuario bloqueado.")`, mesma exceção
  usada em todo o resto do sistema para este caso.
- **`AuthService.rotate_refresh_token`**: usava uma mensagem/status
  genéricos (401, "Usuario nao encontrado ou bloqueado.") misturando
  duas causas distintas. Separado em `UnauthorizedException` (401,
  token/usuário não encontrado) e `ForbiddenException` (403, "Usuario
  bloqueado."), consistente com o resto da aplicação.
- **`app/routes/auth.py`**: `_raise_http_error` não tinha branch para
  `ForbiddenException` (caía no default 400) — necessário para as duas
  correções acima retornarem o status HTTP correto.
- **`PostService.delete_post`**: não impedia a exclusão de um post com
  qualquer `PostAccount` já `PUBLISHED`. Como `Post.post_accounts` tem
  `cascade="all, delete-orphan"`, excluir o post apagava em cascata o
  único registro local de uma publicação real no X (`x_post_id`),
  mesmo em posts com falha parcial (`Post.status == FAILED` mas com
  contas `PUBLISHED` misturadas) — caso que o frontend também não
  barrava corretamente (ver `frontend/CHANGELOG.md`). Corrigido para
  recusar (`ConflictException`, 409) sempre que houver ao menos uma
  conta publicada.
- **`backend/requirements.txt`**: `pytest` nunca esteve declarado,
  apesar de `backend/tests/` conter testes reais e da documentação do
  projeto instruir `docker compose exec backend pytest` como comando
  padrão de validação — uma imagem construída do zero
  (`docker compose up --build`) não conseguia rodar a suíte. Adicionado
  `pytest==8.3.4`.
- **`backend/tests/test_routes_admin.py`**: o dublê
  `FakeSubscriptionService` do teste
  `test_get_subscription_returns_subscription_for_admin` nunca foi
  atualizado para acompanhar `SubscriptionService`/`SubscriptionResponse`
  (métodos e campos adicionados por uma feature anterior), causando uma
  falha conhecida e documentada como "pré-existente, não relacionada"
  em várias features seguintes. Corrigido agora que o escopo é
  justamente varrer inconsistências remanescentes. `pytest`: **6
  passaram, 0 falharam** (primeira vez com a suíte inteiramente verde).

Validado ao vivo contra a stack real (Docker Compose): autenticação
completa, administração (planos/assinaturas/Jitter/auditoria), upload
de mídia real (upload/download/isolamento/remoção), CRUD completo de
posts via HTTP, e um script descartável com 40 asserções cobrindo
publicação (1/4 contas, Jitter, retry/idempotência), Publicação
Inteligente (1/2-4/5+ contas, invariantes, indisponibilidade da Groq),
regras de consumo/limites e scheduler — usando dublês, nunca a API real
do X/Groq.

Reconfirmado (sem alteração): as três correções de escalabilidade da
etapa anterior (scheduler um-a-um, batching de variações da Groq,
reuso de conexão HTTP) continuam intactas e em uso.

Item explicitamente identificado e **não** implementado por exigir
funcionalidade nova (fora do escopo desta auditoria): custo
diferenciado por tipo de conteúdo (`app/domain/publication_cost.py`,
ex. "link consome 15 créditos") permanece desconectado do fluxo real de
consumo — toda publicação continua custando exatamente 1 crédito por
conta, independente do conteúdo.

# CHANGELOG — Análise e correções de escalabilidade (10–100 contas conectadas)

Análise arquitetural (leitura de código, sem testes de carga
artificiais) sobre se o XHub suporta com segurança clientes com 10, 20,
50 e 100 contas conectadas (teto do plano Agência). Relatório completo
em `docs/ANALISE_ESCALABILIDADE.md`. Três gargalos reais encontrados e
corrigidos, sem nenhuma migration nem mudança de comportamento visível
ao cliente:

1. **Scheduler** (`app/scheduler.py`): a reivindicação de agendamentos
   vencidos mantinha a mesma transação/conexão do Postgres aberta
   (com os locks `FOR UPDATE SKIP LOCKED`) durante a publicação de até
   `SCHEDULER_BATCH_SIZE` posts inteiros, um a um. Com o Jitter e
   clientes de muitas contas, um único post grande podia represar o
   agendamento de TODOS os outros clientes por horas (o job roda com
   `max_instances=1`). Corrigido para reivindicar (e marcar
   `executed`) um agendamento por vez, em transações de milissegundos,
   liberando o lock antes de qualquer chamada de publicação.
2. **Publicação Inteligente** (`app/services/ai_content_variation_service.py`):
   um post com N contas pedia as N variações de texto em uma única
   chamada à Groq (ex.: 100 de uma vez para o plano Agência), com risco
   de estourar o timeout fixo e de degradar a diversidade das
   variações. Corrigido para dividir automaticamente em lotes de no
   máximo `AI_CONTENT_VARIATION_MAX_BATCH_SIZE` (novo setting, padrão
   20) — sem nenhuma mudança de comportamento para o caso comum (até
   poucas dezenas de contas).
3. **Chamadas à API do X** (`app/oauth/oauth_client.py`): cada chamada
   HTTP (renovação de token, cada chunk de upload de mídia, publicação
   do tweet) abria e fechava sua própria conexão TCP/TLS, mesmo indo
   para o mesmo host — puro overhead crescendo linearmente com o
   número de contas de um post. Corrigido com um `httpx.Client`
   persistente e reaproveitado por toda a vida de cada instância de
   `XOAuthClient`, fechado explicitamente ao final de
   `PostService.publish_post`/`XOAuthService.complete_callback`.

Áreas analisadas e confirmadas SEM gargalo (nenhuma mudança
necessária): idempotência/concorrência de publicação (o commit por
conta já libera a conexão do banco antes do `time.sleep` do Jitter),
pool de conexões do banco, upload de mídia (já feito em streaming por
chunk, nunca carrega o arquivo inteiro em memória).

Risco residual identificado e deliberadamente não alterado: a
publicação imediata (`POST /posts/{id}/publish`) continua síncrona e
pode levar minutos para 100 contas, arriscando timeout de
proxy/navegador antes do fim do processamento (que continua e termina
corretamente em segundo plano). Corrigir isso exigiria tornar a
publicação imediata assíncrona/em segundo plano — uma decisão de
produto (muda a resposta imediata ao usuário), não uma correção técnica
contida; fica registrado como recomendação para decisão futura.

Validação: `pytest` (5 passaram, 1 falha pré-existente e não
relacionada), `python -c "import app.main"`, e scripts descartáveis com
dublês (nunca a API real do X/Groq) confirmando o batching da Groq
(45 variações → 3 chamadas de `[20, 20, 5]`, comportamento idêntico ao
anterior para 4 variações) e a reivindicação um-a-um do scheduler (3
agendamentos de teste processados corretamente, todos marcados
`executed=True`/`attempts=1`).

# CHANGELOG — Jitter: atraso aleatório entre publicações em múltiplas contas

Última grande funcionalidade antes da auditoria final do projeto:
sistema de Jitter para tornar a sequência de publicações em múltiplas
contas menos automatizada. Especificação completa, decisões técnicas
e validação detalhada em `docs/ROADMAP_JITTER.md` — resumo abaixo.

## Regra de negócio

Quando um post é publicado em mais de uma conta, cada publicação (a
partir da segunda) espera um atraso aleatório e independente (uniforme
entre um mínimo e um máximo configuráveis) antes de ocorrer — nunca
antes da primeira, nunca reaproveitando o valor anterior. Post com uma
única conta, ou um retry em que só falta uma conta pendente, não
recebe nenhum atraso.

## Configuração — administrável, sem alteração de código

- **`JitterSettings`** (nova tabela `jitter_settings`, migration
  `e5f6a7b8c9d0`): tabela *singleton* (sempre exatamente uma linha)
  com `min_seconds`/`max_seconds`. Criada sob demanda com os valores
  padrão (`settings.JITTER_DEFAULT_MIN_SECONDS=1.5`/
  `JITTER_DEFAULT_MAX_SECONDS=8.0`) na primeira leitura — nenhuma
  migration de dado, uma única fonte de verdade para o default.
- `PATCH /admin/jitter-settings`: valor passa a valer **imediatamente**
  para a próxima publicação — `JitterService` sempre lê o valor atual
  do banco, nunca cacheado em memória. Valida `min >= 0`,
  `max >= min` e um teto de segurança
  (`settings.JITTER_MAX_ALLOWED_SECONDS=120.0`, evita um valor digitado
  por engano travar a chamada síncrona de publicação). Audita
  `AuditAction.JITTER_SETTINGS_UPDATED` (migration `f6a7b8c9d0e1`).

## Arquitetura — um único ponto de integração no fluxo já existente

- `app/domain/jitter.py`: `sample_jitter_delay_seconds` — função pura
  (sem I/O), mesmo padrão de `app.domain.media_rules`.
- `app/services/jitter_service.py` (`JitterService`): único lugar que
  efetivamente aguarda (`time.sleep`) e loga — nunca decide *quando*
  aplicar, só *quanto* e *como*.
- `app/services/post_service.py` (`PostService.publish_post`): loop
  `for account_index, post_account in enumerate(accounts_to_publish)`
  — se `account_index > 0`, aplica o atraso antes de qualquer efeito
  colateral da próxima conta (token, upload de mídia, publicação).
  Nenhuma outra parte da função foi alterada: idempotência,
  validações de negócio, tratamento de falha, commits individuais por
  conta, Publicação Inteligente e mídia continuam idênticos.
- `app/scheduler.py`: publicação **agendada** usa o mesmo
  `PostService.publish_post` — mesmo Jitter, sem nenhuma lógica nova
  no worker.

## Decisões técnicas

- **`time.sleep` síncrono**: consistente com o resto do backend
  (nenhuma rota `async def`, todas as chamadas externas já são
  bloqueantes via `httpx.Client`).
- **`account_index > 0` como única checagem**: matematicamente já
  cobre as duas regras ("nunca antes da primeira" + "sem atraso com
  uma única conta") sem duplicar validação.
- **Tabela singleton em vez de `.env`**: variáveis de ambiente só são
  lidas na inicialização do processo (`lru_cache`) — exigiria
  reiniciar a aplicação a cada ajuste. Uma linha em banco, lida a cada
  publicação, satisfaz "vale para as próximas publicações sem
  alteração de código" diretamente.
- **Impacto no scheduler (análise explícita)**: `process_due_scheduled_posts`
  processa o lote sequencialmente e só comita a reivindicação
  (`FOR UPDATE SKIP LOCKED`) ao final — o Jitter aumenta o tempo total
  de um tick proporcionalmente, uma consequência esperada e inerente
  ao próprio objetivo da funcionalidade, não uma quebra de garantia:
  `max_instances=1` + `coalesce=True` (já configurados) garantem que
  isso nunca causa sobreposição ou duplicação, só atraso no início do
  próximo tick. Nenhuma mudança na lógica de transação/lock do
  scheduler foi feita.

## Validação

Ciclo completo testado via `curl` contra a API real e via scripts de
integração com um `XOAuthClient` dublê (removidos após validar, nunca
tocaram a API real do X): 1 conta sem atraso (~0.05s) · 4 contas com
Publicação Inteligente — 3 intervalos, todos dentro do range
configurado e com valores distintos entre si, cada conta com seu
texto correto · mídia real + 2 contas — upload por conta e atraso
funcionando juntos, limpeza de arquivo preservada · publicação
agendada com mídia — mesmo Jitter, mesmo caminho de código · falha em
1 de 3 contas — atraso continua entre tentativas, status/erro
corretos · retry com só 1 conta pendente — sem atraso, idempotência
preservada (contas já `PUBLISHED` não reprocessadas) · validação
administrativa (max<min, min negativo, max acima do teto) · audit log
correto, sem vazar dados sensíveis. `pytest`: 5 passaram, 1 falha
pré-existente e não relacionada.

**Arquivos criados:** `app/domain/jitter.py`,
`app/models/jitter_settings.py`,
`app/repositories/jitter_settings_repository.py`,
`app/services/jitter_service.py`, `docs/ROADMAP_JITTER.md`,
`alembic/versions/e5f6a7b8c9d0_create_jitter_settings_table.py`,
`alembic/versions/f6a7b8c9d0e1_add_jitter_settings_updated_to_audit_action_enum.py`.

**Arquivos modificados:** `app/models/enums.py`,
`app/models/__init__.py`, `app/config/settings.py`,
`app/auth/dependencies.py`, `app/services/post_service.py`,
`app/routes/admin.py`, `app/scheduler.py`, `.env.example`.

---

# CHANGELOG — Primeiro acesso obrigatório (troca de senha temporária)

Funcionalidade de segurança: toda conta criada por um administrador
nasce com uma senha TEMPORÁRIA — no primeiro login, o usuário é
obrigado a defini-la de novo antes de acessar qualquer rota protegida.
O mesmo ciclo se repete após uma redefinição administrativa de senha.
Especificação completa, decisões técnicas e validação detalhada em
`docs/ROADMAP_PRIMEIRO_ACESSO.md` — resumo abaixo.

## Modelo de dados

- **`User.must_change_password`** (nova coluna, migration
  `c3d4e5f6a7b8`): `True` por padrão para contas novas (aplicado
  explicitamente em `UserService.create_user`); usuários **existentes**
  foram migrados com `False`, preservando o acesso normal de quem já
  usava o sistema antes desta funcionalidade.
- **`AuditAction.USER_PASSWORD_RESET`** (migration `d4e5f6a7b8c9`):
  nova ação de auditoria para a redefinição administrativa — nunca
  registra a senha em si, apenas o fato de que ocorreu.

## Gate de acesso — um único ponto de checagem

- `app/domain/policies.ensure_password_change_not_required` (mesmo
  padrão de `ensure_user_not_blocked`, já existente).
- `app/core/exceptions.PasswordChangeRequiredException` → mapeada para
  **HTTP 428 Precondition Required** (RFC 6585), deliberadamente
  distinta de 401/403 para o frontend saber redirecionar em vez de
  tratar como sessão inválida ou acesso negado genérico.
- `app/auth/dependencies.get_current_user` passou a aplicar esse gate.
  Como `get_current_client`/`get_current_admin` dependem de
  `get_current_user`, **toda rota protegida do XHub herda a proteção
  automaticamente** — nenhuma rota individual precisou ser alterada.
- Nova dependency `get_current_user_for_password_change` (resolve o
  usuário autenticado SEM aplicar o gate) — usada exclusivamente pela
  única rota que pode funcionar durante o primeiro acesso obrigatório:
  `POST /auth/change-password`.

## Conclusão do primeiro acesso

- `POST /auth/change-password` (`UserService.complete_first_access`):
  troca a senha (exige apenas a nova senha — o usuário já provou
  conhecer a atual ao fazer login), valida que é diferente da atual,
  zera `must_change_password`, e **revoga todas as sessões (refresh
  tokens) do usuário** (`RefreshTokenRepository.revoke_all_for_user`,
  novo método) — qualquer sessão antiga precisa autenticar de novo.
- A senha temporária deixa de funcionar **imediatamente**: há uma
  única coluna `password_hash`, sobrescrita — nunca existe um estado
  em que as duas senhas sejam válidas ao mesmo tempo.

## Redefinição administrativa

- `POST /admin/users/{user_id}/reset-password`
  (`UserService.reset_password`): gera uma senha temporária **aleatória**
  (`app/auth/password.generate_temporary_password`, 16 caracteres, sem
  caracteres ambíguos), marca `must_change_password=True` de novo,
  revoga todas as sessões ativas. Retornada em texto puro **apenas
  nesta resposta** — nunca persistida nem logada; o administrador
  nunca vê a senha atual do usuário, só a nova temporária que ele
  mesmo gerou.
- `TokenResponse`/`UserResponse` (ambos os módulos de rota) ganharam
  `must_change_password`, para o frontend saber o estado sem precisar
  de uma chamada extra (que seria bloqueada com 428).

## Validação

- Ciclo completo testado via `curl` contra a API real (não apenas
  dublês): criação → login com senha temporária → 428 em `/auth/me`,
  `/twitter-accounts`, `/posts` → `change-password` rejeita mesma
  senha e senha curta → sucesso → login com senha antiga falha (401)
  → login com senha nova funciona e libera as rotas → refresh token
  antigo revogado (401) → reset administrativo → 428 imediato mesmo
  com o access token antigo ainda tecnicamente válido → novo ciclo de
  primeiro acesso idêntico → audit log correto (`details=null`, sem
  vazar a senha) → usuário comum não pode resetar senha de terceiros
  (403).
- `pytest`: 5 passaram, 1 falha pré-existente e não relacionada
  (dublê desatualizado de uma mudança anterior, não desta tarefa) —
  `conftest.py`/`test_routes_auth.py` atualizados para incluir o novo
  campo `must_change_password` nos dublês/asserções.

**Arquivos criados:** `docs/ROADMAP_PRIMEIRO_ACESSO.md`,
`alembic/versions/c3d4e5f6a7b8_add_must_change_password_to_users.py`,
`alembic/versions/d4e5f6a7b8c9_add_user_password_reset_to_audit_action_enum.py`.

**Arquivos modificados:** `app/models/user.py`,
`app/models/enums.py`, `app/domain/contexts.py`,
`app/domain/policies.py`, `app/core/exceptions.py`,
`app/auth/password.py`, `app/auth/dependencies.py`,
`app/repositories/refresh_token_repository.py`,
`app/services/user_service.py`, `app/routes/auth.py`,
`app/routes/admin.py`, `app/scripts/create_admin.py`,
`tests/conftest.py`, `tests/test_routes_auth.py`.

---

# CHANGELOG — Correção pós-deploy: endpoints v2 de upload de mídia do X

Ao testar com uma conta real reconectada, o upload falhava com
`400 Invalid Request: Missing media field in JSON` no INIT. Investigação
(docs oficiais + teste diagnóstico direto contra a API real, com
autorização do usuário) revelou que o X reestruturou o upload de mídia
v2: não é mais um único endpoint com campo `command`, e sim caminhos
REST dedicados por etapa:

- `POST /2/media/upload/initialize` — corpo **JSON** (`media_type`,
  `total_bytes`, `media_category`) → `data.id`.
- `POST /2/media/upload/{id}/append` — multipart (`media` +
  `segment_index`).
- `POST /2/media/upload/{id}/finalize` — sem corpo → `data.processing_info`.
- `GET /2/media/upload/{id}/status` — mesmo padrão de caminho (não
  validado contra a API real ainda — só entra em jogo para gif/vídeo).

`XOAuthClient` reescrito (`_media_initialize`/`_media_append`/
`_media_finalize`/`_wait_for_media_processing`, unificados sobre um
novo `_media_request` genérico) para usar os caminhos corretos.
Validado contra a API real: INIT e APPEND concluídos com sucesso
(`media_id` real retornado); FINALIZE bloqueado por `402 Payment
Required: credits depleted` — falha de billing da conta do X do
usuário, não da implementação, confirmando que autenticação
(Bearer OAuth2 + `media.write`) e protocolo estão corretos.

Uma correção anterior nesta mesma sessão (documentada abaixo) já havia
trocado a URL do endpoint legado v1.1 pela v2 — essa troca de URL
estava certa, mas o formato do corpo (multipart com `command=INIT`)
ainda seguia o padrão antigo, o que só ficou evidente ao testar contra
a API real.

**Arquivos modificados:** `app/oauth/oauth_client.py`,
`docs/ROADMAP_MEDIA.md`.

---

# CHANGELOG — Suporte completo a mídia (imagem/gif/vídeo) na publicação

Implementação completa de mídia como parte da publicação (não uma
funcionalidade separada), incluindo integração real com o protocolo de
upload de mídia do X e compatibilidade total com a Publicação
Inteligente (que continua atuando só sobre o texto). Especificação
completa, decisões técnicas e validação detalhada em
`docs/ROADMAP_MEDIA.md` — resumo abaixo.

## Modelo de dados

- **`PostMedia`** (nova tabela `post_media`, migration
  `a1b2c3d4e5f6`): `post_id` nullable (mídia é enviada e validada
  ANTES do post existir — mesmo fluxo do compositor do X), `user_id`
  (dono, independente de anexação), `media_type` (enum nativo
  `image`/`gif`/`video`), `storage_path`, `content_type`,
  `file_size_bytes`, `position`. `Post.media` — relationship ordenada,
  cascade delete.
- **`TwitterAccount.profile_image_url`** (migration `b2c3d4e5f6a7`):
  URL da foto de perfil real da conta no X (antes só existiam as
  iniciais do nome no frontend).

## Regras de negócio (`app/domain/media_rules.py`)

- Até 4 arquivos por post; imagem (JPEG/PNG/WEBP) até 5MB; GIF até
  15MB (sozinho, não combina com outra mídia); vídeo MP4 até 512MB
  (sozinho, não combina com outra mídia) — mesmos limites/combinações
  da API oficial do X.

## Armazenamento (`app/core/media_storage.py`)

- Disco local, streaming (nunca carrega o arquivo inteiro em memória),
  organizado por usuário, sob `settings.MEDIA_STORAGE_DIR` (padrão
  `media_storage/`, dentro do bind mount `./backend:/app` — sobrevive
  a restarts sem exigir volume Docker novo). Adicionado a `.gitignore`.

## Upload/gerenciamento (`MediaService`, `app/routes/media.py`)

- `POST /media/upload` (multipart), `GET /media/{id}/file` (download
  autenticado, ownership-checked, `FileResponse` streaming),
  `DELETE /media/{id}` (só mídia ainda não anexada a um post).

## Integração com posts (`PostService`)

- `create_post(media_ids=...)`: valida posse + combinação ANTES de
  criar o `Post`; anexa na mesma transação dos `PostAccount`.
- `delete_post`: apaga os arquivos do disco ANTES de apagar o `Post`
  (cascade do banco não sabe tocar o filesystem).
- `publish_post`: para cada `PostAccount` pendente, envia a mídia ao X
  **uma vez por conta** (cada conta tem seu próprio token/biblioteca de
  mídia no X) via `XOAuthClient.upload_media`, e só então publica o
  tweet com `media_ids`. Funciona para publicação imediata E agendada
  sem nenhuma mudança no worker (`app/scheduler.py`) — ambos reusam o
  mesmo `publish_post`.

## Integração real com a API do X (`XOAuthClient`)

- `upload_media`: protocolo oficial de upload chunked no endpoint v2
  nativo (`POST https://api.x.com/2/media/upload`) — `INIT` → `APPEND`
  (chunks de 4MB) → `FINALIZE` → `STATUS` (polling para o
  processamento assíncrono de gif/vídeo). Reaproveita
  `_extract_error_detail` (mesma preservação de motivo original de
  erro já usada em `publish_post`). **Correção pós-implementação:** a
  primeira versão usava por engano o endpoint legado v1.1
  (`upload.twitter.com/1.1/media/upload.json`); ao ser questionado
  sobre aderência à documentação oficial, verifiquei contra
  `docs.x.com/x-api/media` e confirmei que o X migrou este endpoint
  para `api.x.com/2/media/upload` — corrigido antes de qualquer teste
  com conta real (protocolo INIT/APPEND/FINALIZE/STATUS e autenticação
  Bearer OAuth2 user-context com escopo `media.write` permaneceram
  corretos, só a URL estava desatualizada).
- `publish_post(media_ids=...)`: inclui `{"media": {"media_ids":
  [...]}}` no payload de `POST /2/tweets`.
- `X_OAUTH_SCOPES` passou a incluir `media.write` (necessário para o
  upload). **Contas conectadas antes desta mudança precisam ser
  reconectadas** para publicar posts com mídia — o escopo é definido
  na autorização, não pode ser adicionado retroativamente a um token
  já emitido.
- `get_authenticated_user` agora pede `user.fields=profile_image_url`
  e faz upgrade de resolução da foto (`_normal` → `_400x400`, mesma
  URL/CDN, sem chamada extra).

## Bug pré-existente corrigido incidentalmente

- `PostService.publish_post` usava `ConflictException` sem importá-la
  (`NameError` garantido no caminho "post já está sendo publicado por
  outra requisição" — uma corrida de concorrência legítima). Notado ao
  tocar o bloco de imports para esta tarefa; corrigido junto por ser
  uma linha isolada e obviamente quebrada, não uma mudança de escopo.

## Validação

- `alembic upgrade head` aplicado sem erro; schema conferido via
  `psql \d post_media`.
- `python -c "import app.main"` limpo.
- `pytest`: 5 passaram, 1 falha pré-existente e não relacionada
  (`test_get_subscription_returns_subscription_for_admin` — dublê de
  teste desatualizado de uma mudança anterior, não desta tarefa).
- Integração ponta a ponta via `curl` contra a API real: upload de
  imagem, download autenticado com bytes idênticos ao original, 401
  sem token, 404 para outro usuário (sem revelar existência), remoção
  com limpeza do arquivo em disco.
- Script de integração dentro do container (removido após validar):
  `create_post(media_ids=...)` anexa corretamente; `publish_post`
  chama `upload_media` uma vez por conta ANTES de
  `publish_post(media_ids=...)` com os parâmetros certos (testado com
  um `XOAuthClient` dublê, sem tocar a API real do X); `delete_post`
  remove o arquivo do disco.
- Não validado (sem conta real do X disponível neste ambiente): o
  fluxo completo contra `api.x.com/2/media/upload`, incluindo o caso
  assíncrono de vídeo/gif. Recomenda-se um teste manual com uma conta
  reconectada (escopo `media.write`) antes do primeiro uso em
  produção.

**Arquivos criados:** `app/domain/media_rules.py`,
`app/core/media_storage.py`, `app/models/post_media.py`,
`app/repositories/post_media_repository.py`,
`app/services/media_service.py`, `app/schemas/media.py`,
`app/routes/media.py`,
`alembic/versions/a1b2c3d4e5f6_create_post_media_table.py`,
`alembic/versions/b2c3d4e5f6a7_add_profile_image_url_to_twitter_accounts.py`,
`docs/ROADMAP_MEDIA.md`.

**Arquivos modificados:** `app/models/enums.py`, `app/models/post.py`,
`app/models/twitter_account.py`, `app/models/__init__.py`,
`app/repositories/post_repository.py`, `app/services/post_service.py`,
`app/routes/post.py`, `app/oauth/oauth_client.py`,
`app/oauth/oauth_service.py`, `app/services/twitter_account_service.py`,
`app/routes/twitter_account.py`, `app/auth/dependencies.py`,
`app/scheduler.py`, `app/main.py`, `app/config/settings.py`,
`.env.example`, `.gitignore`.

---

# CHANGELOG — Auditoria técnica completa da Publicação Inteligente

Auditoria dos 10 pontos pedidos (prompt, preservação de regras de negócio,
qualidade das variações, fluxo por quantidade de contas, retry/validação,
segurança, casos extremos, performance/custo, código, validação final).
Ver resposta da auditoria para o relatório completo item a item. Resumo
das duas correções aplicadas (validadas empiricamente antes de aplicar,
nenhuma por tentativa e erro):

## 1. Bug real: `preserves_invariants` rejeitava URLs preservadas corretamente

**Problema:** `_URL_PATTERN` em `app/domain/content_invariants.py` captura
o caminho de uma URL com `[^\s]*` (tudo que não é espaço) — isso inclui
pontuação de fim de frase colada à URL (`.`, `,`, `!`, `)` etc.). Quando a
IA reescreve a frase ao redor de uma URL (mantendo a URL 100% intacta,
como exigido), a pontuação vizinha muda naturalmente — e a função
comparava "URL + pontuação" em vez de só a URL, rejeitando variações
válidas.

**Evidência (antes da correção):**
```python
preserves_invariants(
    "Confira em https://exemplo.com/produto123. Não perca!",
    "Confira em https://exemplo.com/produto123, e aproveite!",
)  # False -- ambas tem a MESMA URL, só a pontuação ao redor mudou
```

**Correção:** `_strip_trailing_url_punctuation` remove um conjunto fixo de
pontuação de encerramento (`.,;:!?)]}'"`) do final de cada URL capturada,
antes da comparação. Validado com 5 cenários (pontuação diferente,
parênteses, query string com `&`/`=` preservada, URL genuinamente
diferente ainda rejeitada corretamente, múltiplas URLs) — todos passam.

**Impacto:** reduz rejeições falso-positivas de variações válidas, o que
por sua vez reduz retries desnecessários à Groq (custo) e reduz o risco
de falha em publicações de 5+ contas (regra obrigatória, sem fallback).

**Arquivos:** `app/domain/content_invariants.py`.

## 2. Melhoria de qualidade no prompt (validada com chamadas reais à Groq)

**Problema identificado empiricamente:** gerei 5 variações reais (texto
com URL, hashtags, menção, emoji e CTA com cláusula de urgência) com o
prompt original. Duas observações concretas:
- Uma das 5 variações omitiu "é por tempo limitado" (a cláusula de
  urgência do CTA), mantendo só o verbo de ação — violação sutil da
  regra 6 do próprio prompt ("nunca remova informação existente").
- As 5 variações, apesar de vocabulário diferente, seguiam o MESMO
  esqueleto de frase (emoji sempre logo no início, hashtags+menção
  sempre agrupadas no fim) — risco de continuar parecendo padronizado
  para detecção de conteúdo repetitivo, mesmo sem repetir palavras.

**Correção:** reforcei a regra 4 (CTA deve incluir a cláusula de
urgência/escassez associada) e a regra 8 (variar também a ESTRUTURA da
frase — ordem dos elementos, ponto de partida, posição de emoji/link/
hashtags — não só o vocabulário).

**Validado com o mesmo texto de teste, antes/depois:** as 5 novas
variações preservaram "por tempo limitado" em todas, e cada uma tem
estrutura visivelmente diferente (uma começa pela urgência, outra pelo
emoji, outra pela menção, outra por uma pergunta implícita). Confirmado
programaticamente que `preserves_invariants` continua `True` e
`has_duplicates` continua `False` para as 5 -- a mudança só afeta a
qualidade estocástica da resposta da IA, nunca a garantia determinística
de preservação (que independe do que o prompt pede).

**Custo:** prompt subiu de ~886 para ~1050 caracteres (system prompt),
tokens por chamada de 5 variações foram de 609 para 752 (+23%) — a custo
absoluto continua desprezível (frações de centavo por chamada, llama-3.3-
70b-versatile via Groq), tradeoff claramente favorável à qualidade.

**Arquivos:** `app/services/ai_content_variation_service.py`
(`_build_system_prompt`).

## Pontos auditados e aprovados sem alteração

- Fluxo por quantidade de contas (1 / 2-4 / 5+) -- constantes
  compartilhadas entre `PostService` e `AIContentVariationService` via
  `app.domain.policies`, sem divergência.
- Retry/cache: no máximo 2 chamadas à Groq por preview (lote inicial +
  complemento), cache só guarda resultado já validado, checagem final de
  duplicata redundante mas correta.
- Segurança: a garantia de preservação de URLs/hashtags/@menções/emojis
  é 100% determinística (`content_invariants`), não depende da IA
  obedecer o prompt -- mesmo uma tentativa de prompt injection via texto
  do usuário seria pega pela validação mecânica.
- Edição manual revalidada no backend (`PostService._validate_rendered_texts`)
  com o mesmo `preserves_invariants`, incluindo checagem de duplicata
  obrigatória para 5+ contas na confirmação (não só no preview).
- `AIContentVariationService`/`GroqClient`/schemas/rotas seguem
  exatamente a arquitetura Routes → Services → Repositories já
  documentada, sem regra de negócio na rota.

**Limitação conhecida, não corrigida (baixo risco real):** o regex de
URL exige um domínio com pelo menos um ponto -- URLs tipo
`http://localhost:8080` ou IP:porta sem domínio não são detectadas.
Irrelevante na prática (posts reais em redes sociais não usam esse
formato), documentado aqui em vez de uma correção especulativa.

## Validação

- `from app.main import app` importa sem erro, 44 rotas.
- `POST /intelligent-publication/preview` testado ao vivo (404 limpo
  para conta inexistente, sem crash).
- 3 chamadas reais à Groq feitas durante a auditoria (antes/depois do
  prompt) para avaliar qualidade com dados reais, não só teoria.

---

# CHANGELOG — Privacidade em /admin/posts: conteúdo do post removido da visão admin

Ajuste sobre a tela de auditoria de publicações da rodada anterior:
`AdminPostResponse` mostrava o texto do post (truncado) na tabela. Por
pedido explícito de privacidade, o campo `text` foi removido por
completo da resposta -- o administrador só vê status (do post e por
conta do X) e o motivo técnico de falha, nunca o conteúdo escrito pelo
usuário.

**Arquivos:** `app/routes/admin.py` (`AdminPostResponse` e
`_to_admin_post_response`).

**Validado:** confirmado via schema OpenAPI que `text` não existe mais
em `AdminPostResponse`, e via chamada real que a resposta não traz esse
campo em nenhum post.

---

# CHANGELOG — Registro detalhado do motivo de falha de publicação (admin-only)

Contexto: diagnóstico anterior confirmou que uma falha de publicação
ocorria de verdade, mas sem detalhe do motivo (`PostAccount.error_message`
só guardava mensagens genéricas como "Falha ao publicar post no X.").
Este item implementa a captura do motivo exato, preservando a lógica de
publicação existente (`PostService.publish_post`) sem nenhuma alteração —
só o texto das exceções levantadas por `XOAuthClient` mudou.

## 1. `XOAuthClient` passa a preservar a resposta original da API do X

**Problema:** cada branch de erro (`401`/`403`/`429`/`5xx`/genérico) em
`publish_post` e `refresh_access_token` levantava uma exceção com
mensagem fixa em português, descartando o `status_code` e o corpo da
resposta reais do X — impossível saber se a falha foi por token
expirado, permissão, limite de requisições, falta de créditos ou
qualquer outro motivo.

**Solução:** novo método `XOAuthClient._extract_error_detail(response)`,
que lê o corpo da resposta (formato RFC 7807 usado pela API v2 do X —
`title`/`detail`/`type` — com fallback para `errors[].message` e para o
texto cru se não for JSON) e monta uma mensagem como `"{status_code} -
{contexto}: {title}: {detail}"`. Cada branch existente continua
levantando o **mesmo tipo** de exceção de antes (`UnauthorizedException`,
`ForbiddenException`, `ServiceUnavailableException`, `BadRequestException`)
— só o conteúdo da mensagem mudou, então nenhum comportamento de
`PostService.publish_post` (idempotência, commits por conta, ordem de
validação) foi alterado.

Também adicionado tratamento explícito de `httpx.TimeoutException` e
`httpx.RequestError` (antes não capturados: um timeout/erro de conexão
caía no branch genérico "Erro inesperado ao publicar no X." do
`PostService`, sem indicar a natureza do problema) — agora levantam
`ServiceUnavailableException("Timeout ao conectar com a API do X.")` ou
`"Erro de conexao com a API do X: {detalhe}"`, cobrindo os cenários
"Timeout" e "Erro de conexão" pedidos explicitamente.

`refresh_access_token` recebeu o mesmo tratamento — cobre o cenário
"Access Token expirado" quando a renovação automática também falha.

**Validado ao vivo, com a conta real do X que estava sem créditos:**
uma tentativa de publicação real capturou `error_message =
"402 - Falha ao publicar no X: Payment Required: credits depleted"` —
confirmando com evidência direta a causa raiz suspeitada na etapa
anterior de diagnóstico (que havia ficado sem confirmação por falta
exatamente desse detalhe).

**Arquivos:** `app/oauth/oauth_client.py`.

## 2. Motivo detalhado exposto **somente** ao administrador

**Decisão:** `error_message` já era exposto ao cliente em `GET /posts`
(campo pré-existente em `PostAccountResponse`) com uma mensagem
genérica. Agora que o conteúdo ficou técnico (status HTTP + corpo bruto
da resposta do X), continuar expondo isso ao cliente vazaria detalhe de
API desnecessário. Removido de `PostAccountResponse`
(`app/routes/post.py`) — `GET /posts`/`GET /posts/{id}` não retornam
mais esse campo.

**Nova visão administrativa:** `GET /admin/posts` (`get_current_admin`,
somente leitura, paginado, filtro opcional por `status_filter`), listando
posts de **todos** os usuários com nome/e-mail do dono e o detalhamento
por conta incluindo `error_message`. Reaproveita `PostService`/
`PostRepository` já existentes — novo método `PostRepository.list_all`
(sem filtro por `user_id`, com eager-load de `Post.user`) e
`PostService.list_all_posts`, sem tocar em nenhum método usado pelo
fluxo de publicação.

**Validado:** confirmado via schema OpenAPI que `PostAccountResponse`
(cliente) não tem mais o campo `error_message` enquanto
`AdminPostAccountResponse` (admin) tem; confirmado que um cliente
recebe `403` ao tentar acessar `/admin/posts` diretamente.

**Arquivos:** `app/repositories/post_repository.py`,
`app/services/post_service.py`, `app/routes/admin.py`,
`app/routes/post.py`.

---

# CHANGELOG — Auditoria funcional completa: bug crítico de migration, consumo do usuário para o admin

## 1. Bug crítico (bloqueante): enum `audit_action` desatualizado no Postgres

**Problema:** `app.models.enums.AuditAction` ganhou os membros `USER_CREATED`
e `PLAN_UPDATED` em algum momento do desenvolvimento, mas nenhuma migration
foi criada para adicioná-los ao tipo nativo `audit_action` do Postgres (que
foi criado com apenas 13 labels, na migration `5f1c7a9e2b3d`). Resultado:
**toda chamada a `POST /admin/users` — a ÚNICA forma de criar uma conta no
XHub, já que não há auto cadastro — falhava com 500**
(`sqlalchemy.exc.DataError: invalid input value for enum audit_action:
"USER_CREATED"`), porque `AuditLogService.record()` roda na mesma transação
da criação do usuário. `PATCH /admin/plans/{plan_id}` falhava da mesma forma
com `PLAN_UPDATED`. Isso foi descoberto ao testar o fluxo completo de ponta a
ponta (criar cliente → logar → consultar `/me/subscription`) durante a
auditoria — sem ele, nenhum cliente novo conseguia ser criado pela UI admin,
o que por sua vez explica boa parte da dificuldade em testar os fluxos de
cliente.

**Correção:** nova migration `b4c5d6e7f8a9`, seguindo exatamente o padrão já
estabelecido no projeto para esse tipo de correção (`ALTER TYPE ... ADD
VALUE` em `autocommit_block`, mesma técnica da migration `9b2f6a1d7e4c`, que
resolveu o mesmo problema para `post_status`/`PENDING`). Validado ao vivo:
criação de cliente e atualização de plano voltaram a funcionar (200/201) após
`alembic upgrade head`.

**Arquivos:** `alembic/versions/b4c5d6e7f8a9_add_user_created_and_plan_updated_to_audit_action_enum.py` (novo).

## 2. `GET /me/subscription` retornando 404 — investigado, não é bug

**Investigação:** confirmado ao vivo que a rota está registrada corretamente
(`/api/v1/me/subscription`), o path do frontend bate exatamente, e o router
está incluído em `main.py`. O 404 é **comportamento correto e intencional**
para contas administrativas (criadas sem `Subscription`, por design — ver
`POST /admin/users`). Testado com uma conta cliente com assinatura ativa:
`200 OK` com todos os campos esperados. A confusão original muito
provavelmente vinha do bug #1 acima (impossível criar um cliente para testar).

## 3. Consumo do usuário incompleto na visão administrativa

**Problema:** `GET /admin/subscriptions/{id}` e `GET /admin/users/{id}/subscription`
retornavam apenas `used_posts`/`extra_posts` em números crus, sem o limite do
plano para comparação, sem contas conectadas e sem posts disponíveis no
ciclo — o admin não conseguia avaliar se um usuário estava perto do limite. O
endpoint de cliente (`/me/subscription`) já expunha isso; faltava no lado
admin.

**Correção:** `SubscriptionResponse` ganhou `plan` (nome/preço/limites),
`used_accounts` e `available_posts`, calculados pela mesma política de
domínio já usada em `/me/subscription`
(`SubscriptionService.to_domain_context`/`get_available_posts`). Como
`_to_subscription_response` é compartilhado por 7 endpoints (consulta e as 5
ações de renovar/bloquear/expirar/créditos extras), a melhoria se propaga
automaticamente para todos eles.

**Arquivos:** `app/routes/admin.py`.

## Validação

- `from app.main import app` importa sem erro, 43 rotas registradas.
- Ciclo completo testado ao vivo contra o Postgres real: criar admin →
  logar → criar cliente com plano → logar como cliente → `GET
  /me/subscription` (200) → `GET /admin/users/{id}/subscription` como admin
  (200, com plano/limites/consumo) → `PATCH /admin/plans/{id}` (200).

---

# CHANGELOG — Novos endpoints de leitura (assinatura do cliente, métricas e auditoria)

Esta rodada adiciona três capacidades de **leitura** que faltavam para o
frontend, sem tocar em nenhuma regra de negócio já consolidada
(autenticação, publicação, agendamento, gestão administrativa de
usuários/planos/assinaturas). Todos os endpoints reaproveitam os
models/services/repositories de Subscription, Post, User e AuditLog já
existentes — nenhuma tabela nova, nenhuma migração.

## 1. `GET /me/subscription` — assinatura do próprio usuário

**Motivação:** não existia nenhum endpoint que um usuário comum (cliente)
pudesse chamar para ver a própria assinatura. Todos os `GET` de
Subscription eram administrativos (`get_current_admin`, operando sobre
qualquer usuário via id na URL).

**Solução:** novo router `app/routes/me.py` (prefixo `/me`, autorização
`get_current_user`), com `GET /me/subscription`. Descobre a assinatura a
partir do token (nunca recebe id por parâmetro) e devolve
`MySubscriptionResponse`: status, vigência, `used_posts`/`extra_posts`,
`available_posts` (calculado pela mesma política de domínio da
publicação), `used_accounts` (contas do X conectadas) e o plano associado
(`plan`) com seus limites. Retorna 404 quando o usuário não tem
assinatura — caso típico de contas administrativas.

**Arquivos:** `app/routes/me.py` (novo), `app/main.py` (registro do
router).

## 2. `GET /admin/stats` — métricas agregadas da plataforma

**Motivação:** o dashboard administrativo precisava de uma visão agregada
(total de usuários, assinaturas por status, volume de posts) que nenhum
endpoint expunha.

**Solução:** `GET /admin/stats` (`get_current_admin`, somente leitura),
retornando `AdminStatsResponse` com `total_users`,
`active/blocked/expired_subscriptions`, `total_posts` e
`published_posts`. As contagens usam métodos novos e enxutos nas camadas
já existentes:
- `SubscriptionRepository.count_by_status` + `SubscriptionService.count_by_status`.
- `PostRepository.count_by_status` + `PostService.count_by_status`.
- `UserService.count` / `PostService.count` (herdados de `BaseService`).

**Arquivos:** `app/routes/admin.py`,
`app/repositories/subscription_repository.py`,
`app/services/subscription_service.py`,
`app/repositories/post_repository.py`, `app/services/post_service.py`.

## 3. `GET /admin/audit-logs` — consulta da trilha de auditoria

**Motivação:** o backend já gravava auditoria em toda ação administrativa
(`AuditLogService.record`), mas não havia nenhum `GET` para consultá-la.

**Solução:** `GET /admin/audit-logs` (`get_current_admin`, paginado por
`offset`/`limit`), das mais recentes para as mais antigas via
`AuditLogService.list_recent` (já existente). Resposta
`AuditLogResponse` inclui `actor_name` (nome do autor resolvido pela
relationship `AuditLog.actor`, `None` para autores já removidos, já que o
FK usa `ON DELETE SET NULL`). A trilha continua append-only — este
endpoint é estritamente de leitura.

**Arquivos:** `app/routes/admin.py`.

## Validação

- `from app.main import app` importa sem erro; as 3 rotas novas aparecem
  registradas (`/api/v1/me/subscription`, `/api/v1/admin/stats`,
  `/api/v1/admin/audit-logs`) — total de 38 rotas.
- Nenhuma alteração em models/migrações; nenhum endpoint ou regra
  existente foi modificado.

---

# CHANGELOG — Correções da auditoria técnica (bootstrap, cadastro, agendamento, observabilidade e publicação)

Esta atualização resolve os problemas identificados na auditoria técnica mais
recente do backend XHub, cobrindo os cinco itens **críticos**, os dois **altos**,
os três **médios** e os dois **baixos** com ação de código associada
(os demais itens baixos eram apenas de documentação, também atualizada).
Nenhuma correção anterior foi revertida ou refeita — a camada de domínio
já madura (locks `FOR UPDATE`, idempotência de publicação, criptografia
Fernet, PKCE de uso único, constraint de assinatura ativa única, migração
cuidadosa de enum) foi preservada integralmente.

Regras de negócio confirmadas como definitivas e usadas como guia de todas
as decisões abaixo: **não há auto cadastro**; usuários são criados
exclusivamente por administradores, que escolhem o plano explicitamente;
**não há trial automático**; o catálogo oficial de planos define apenas
limites/características (preço é definido manualmente pelo administrador);
**agendamento de posts é funcionalidade do produto** e foi implementado,
não removido.

---

## 🔴 Críticos

### 1. Sistema não subia operacional sem SQL manual (planos)

**Problema:** `PlanService.sync_official_plans()` existia e fazia upsert
correto do catálogo oficial, mas nunca era chamado em lugar nenhum. Um
deploy novo nascia com `plans` vazia e `POST /admin/users` (que exige
`plan_id` válido) não tinha como funcionar sem inserção manual no banco.

**Solução adotada:** chamar `sync_official_plans()` automaticamente no
`lifespan` de startup do FastAPI, com uma sessão de banco dedicada
(fora do ciclo de vida de requisição HTTP), sem exigir nenhuma
intervenção manual. Como reforço operacional, foi adicionado também
`POST /admin/plans/sync`, para re-sincronizar o catálogo sob demanda
(ex.: quando o catálogo oficial ganha um novo plano com a aplicação já
no ar, sem precisar reiniciar o processo). O preço de planos já
existentes nunca é sobrescrito pela sincronização (mantendo a regra de
que o preço é definido manualmente pelo administrador) — esse
comportamento já estava correto em `PlanService` e foi preservado sem
alteração.

**Arquivos modificados/criados:**
- `app/core/bootstrap.py` (novo) — função `sync_official_plans()` chamada no startup.
- `app/main.py` — `lifespan` chamando o bootstrap e iniciando/finalizando o scheduler.
- `app/routes/admin.py` — novo endpoint `POST /admin/plans/sync`.

**Impacto:** qualquer ambiente novo (dev, staging, produção) fica
operacional assim que a aplicação sobe e as migrations são aplicadas —
sem nenhum passo manual no banco. Nenhum contrato de API existente foi
alterado; apenas uma rota nova foi adicionada.

---

### 2. Cadastro público (`/auth/register`) criava contas inutilizáveis

**Problema:** o endpoint público criava usuários sem nenhuma
`Subscription`, gerando contas que falhavam imediatamente em qualquer
ação relevante — e contradizia a regra de negócio já documentada no
próprio código (`app/routes/admin.py`).

**Solução adotada:** conforme a regra de negócio definitiva (não existe
auto cadastro), o endpoint `POST /auth/register` foi **removido por
completo**. O único fluxo de criação de usuários agora é o
administrativo (`POST /admin/users`), que já exigia a escolha explícita
do plano e já criava a `Subscription` na mesma transação. As variáveis
`DEFAULT_TRIAL_PLAN_NAME`/`DEFAULT_TRIAL_PERIOD_DAYS`, que existiam no
`.env` mas nunca eram usadas (nem declaradas em `Settings`) e
contradiziam a regra de "sem trial automático", foram removidas dos
arquivos de ambiente.

**Arquivos modificados:**
- `app/routes/auth.py` — remoção da rota `/auth/register` e do schema `RegisterRequest`.
- `app/middleware/rate_limit.py` — remoção da referência a `/auth/register` da lista de rotas protegidas por rate limit.
- `backend/.env`, `backend/.env.example` — remoção das variáveis de trial não utilizadas.

**Impacto:** não é mais possível criar uma conta sem que um
administrador escolha um plano — eliminando a classe inteira de "contas
quebradas" relatada na auditoria. **Mudança de contrato de API:**
`POST /auth/register` deixa de existir (retornará 404). Isso é
intencional e exigido pela regra de negócio definitiva informada.

---

### 3. Agendamento de posts não existia de fato

**Problema:** `schedule_post()`/`cancel_schedule()` só chamavam
`self.not_implemented(...)`; `list_due()` nunca era chamado; não havia
rota, worker, nem processo de background configurado.

**Solução adotada:** implementação completa, reaproveitando a
modelagem de dados já existente (`ScheduledPost`) e a dependência
`apscheduler` (já listada em `requirements.txt`, sem introduzir
infraestrutura nova como RabbitMQ/Celery/Kafka):

- `ScheduledPostService.schedule_post`/`cancel_schedule` implementados
  de fato, com validação de status do post, checagem de data futura, e
  transição correta do `Post.status` (`PENDING → SCHEDULED` e de volta).
- Novas rotas `POST /posts/{post_id}/schedule` e
  `DELETE /posts/{post_id}/schedule`.
- Novo módulo `app/scheduler.py`: worker in-process
  (`BackgroundScheduler`), iniciado/finalizado no `lifespan` da
  aplicação, que a cada `SCHEDULER_INTERVAL_SECONDS` (30s por padrão)
  processa os agendamentos vencidos usando o fluxo já existente e
  testado de `PostService.publish_post`.
- **Segurança com múltiplos processos/réplicas:** a etapa de
  "reivindicar" agendamentos vencidos usa
  `SELECT ... FOR UPDATE SKIP LOCKED` no Postgres
  (`ScheduledPostRepository.list_due_for_update_skip_locked`, acionado
  via `ScheduledPostService.claim_due`), garantindo que cada
  agendamento seja processado no máximo uma vez mesmo com
  `--workers 2` ou múltiplas réplicas do container — sem exigir nenhum
  coordenador/lock distribuído externo.
- Migração nova adiciona `attempts`/`last_error` em `scheduled_posts`
  para dar visibilidade de tentativas e falhas de processamento
  diretamente no registro do agendamento.

**Arquivos modificados/criados:**
- `app/models/scheduled_post.py` — colunas `attempts`/`last_error`.
- `alembic/versions/d1e2f3a4b5c6_...py` (novo) — migração das novas colunas.
- `app/repositories/scheduled_post_repository.py` — `list_due_for_update_skip_locked`.
- `app/services/scheduled_post_service.py` — implementação completa (antes só `not_implemented`).
- `app/routes/post.py` — rotas `POST`/`DELETE /posts/{post_id}/schedule`.
- `app/auth/dependencies.py` — dependency `get_scheduled_post_service`.
- `app/scheduler.py` (novo) — worker in-process.
- `app/main.py` — start/shutdown do worker no `lifespan`.
- `app/config/settings.py`, `.env`, `.env.example` — `SCHEDULER_ENABLED`, `SCHEDULER_INTERVAL_SECONDS`, `SCHEDULER_BATCH_SIZE`.

**Impacto:** agendamento passa a ser 100% funcional: criar, cancelar e
processar automaticamente no horário certo, reaproveitando toda a
lógica de idempotência/consumo de saldo já validada em `publish_post`.
Nova superfície de API (rotas de schedule); nenhum contrato existente
foi alterado.

---

### 4. Ausência total de logging/observabilidade

**Problema:** nenhum `import logging` no projeto; qualquer exceção não
tratada virava 500 genérico sem nenhum rastro; sem correlation-id; sem
handler global de exceções.

**Solução adotada:** logging estruturado (JSON, um objeto por linha,
via `logging` da stdlib — sem dependências novas), com:
- `app/core/logging_config.py`: formatter JSON + configuração central
  (chamada uma única vez no import de `app.main`), silenciando o ruído
  de bibliotecas de terceiros em produção.
- `app/middleware/request_context.py`: middleware que gera (ou
  reaproveita) um `X-Request-ID` por requisição, guardado em uma
  `contextvar` e automaticamente incluído em todo log emitido durante o
  processamento daquela requisição — sem precisar repassar o valor
  manualmente por todas as camadas.
- Handler global de exceções em `app/main.py`
  (`@app.exception_handler(Exception)`): registra qualquer exceção não
  tratada com stacktrace completo e `request_id` de correlação antes de
  responder 500 genérico ao cliente (sem vazar detalhes internos).
- Logs adicionados nos pontos de maior risco/relevância operacional:
  publicação de posts (sucesso/falha por conta), processamento de
  agendamentos, bootstrap de planos, start/stop do scheduler.

**Arquivos criados/modificados:**
- `app/core/logging_config.py` (novo)
- `app/middleware/request_context.py` (novo)
- `app/main.py` — configuração de logging, middleware, handler global.
- `app/services/post_service.py`, `app/scheduler.py`, `app/core/bootstrap.py` — chamadas de log nos pontos relevantes.

**Impacto:** qualquer incidente em produção agora deixa rastro
(stacktrace + `request_id` + contexto estruturado), permitindo
diagnóstico real, correlação entre múltiplas linhas de log de uma mesma
requisição, e detecção de falhas antes que o cliente precise reclamar.

---

### 5. Dessincronização entre publicação no X e persistência no banco

**Problema:** a chamada real à API do X e a marcação `PUBLISHED` só
eram commitadas juntas, no final da rota. Um crash entre a resposta do
X e esse commit final fazia a linha voltar a `PENDING` (rollback
implícito), e um retry publicaria o mesmo texto de novo no X —
duplicado, visível publicamente.

**Solução adotada (sem outbox/broker externo, aproveitando a stack já
existente):** `PostService.publish_post` agora **commita
imediatamente** após cada efeito externo bem-sucedido, em vez de
esperar o commit único da rota:
1. Renovação de token OAuth do X é commitada de forma independente e
   imediata (muitos provedores rotacionam o refresh token a cada uso —
   se um rollback posterior desfizesse essa renovação, o refresh token
   antigo, já invalidado pelo X, ficaria salvo, quebrando futuras
   renovações).
2. Assim que o X responde com sucesso, o `PostAccount` é marcado
   `PUBLISHED` e **commitado imediatamente**, antes de qualquer outra
   operação (inclusive antes do consumo de saldo) — para que nenhuma
   falha subsequente possa fazer um post genuinamente publicado ser
   rotulado como `FAILED`.
3. O consumo de saldo da assinatura é tentado em seguida; se falhar
   (cenário raro), o post permanece corretamente marcado como
   publicado e o erro é logado como crítico para verificação
   administrativa, em vez de reverter uma publicação que já é real.
4. Falhas de negócio (`BaseAppException`) e falhas inesperadas
   (rede/timeout/bugs) são tratadas separadamente: ambas marcam e
   commitam o `PostAccount` como `FAILED` imediatamente, permitindo
   retry seguro (a idempotência existente — `status != PUBLISHED` não é
   reprocessado — passa a proteger de fato, porque o que já foi
   publicado está sempre commitado antes de qualquer chance de crash).

**Arquivos modificados:**
- `app/services/post_service.py`

**Impacto:** a janela de inconsistência entre o efeito externo
(irreversível) e o banco é reduzida ao mínimo tecnicamente possível
sem outbox pattern (a fração de segundo entre a resposta do X e o
`COMMIT` local), e a garantia de idempotência passa a valer mesmo em
caso de crash do processo. Nenhuma mudança de contrato de API.

---

## 🟠 Altos

### 6. Rate limiting contornável via `X-Forwarded-For` forjado

**Solução:** por padrão, o rate limit agora usa exclusivamente
`request.client.host` (a conexão TCP real, que o cliente não
controla). Confiar em `X-Forwarded-For` passa a ser opt-in explícito
via `TRUST_PROXY_HEADERS=true`, para quando a aplicação realmente rodar
atrás de um proxy/load balancer confiável que sobrescreve esse header.

**Arquivos:** `app/middleware/rate_limit.py`, `app/config/settings.py`, `.env`, `.env.example`.

**Impacto:** o controle de força bruta em `/auth/login` volta a ser
efetivo por padrão, sem quebrar deploys legítimos atrás de proxy (basta
habilitar a flag).

### 7. Rate limiting em memória sem limite de crescimento

**Solução:** além da limpeza por-chave já corrigida, foi adicionada uma
varredura periódica de todo o dicionário (a cada 500 requisições
processadas) que remove chaves cujas entradas já expiraram — cobrindo
também o caso de clientes que fazem uma única leva de requisições e
nunca mais voltam (que antes ficariam ocupando memória indefinidamente,
já que nada mais tocaria aquela chave para disparar a limpeza).

**Arquivos:** `app/middleware/rate_limit.py`.

**Impacto:** crescimento de memória do middleware passa a ser limitado
por uma janela de tempo, não pelo histórico total de clientes únicos.
A limitação estrutural já conhecida (estado em memória local por
processo, não compartilhado entre workers/réplicas) permanece
documentada no código — resolvê-la definitivamente exigiria estado
compartilhado (Redis), fora do escopo desta correção por não haver
necessidade comprovada de introduzir essa infraestrutura agora.

---

## 🟡 Médios

### 9. Corrida em cadastro duplicado gerava 500 em vez de 409

**Solução:** `UserService.create_user` agora captura `IntegrityError`
do SQLAlchemy (que escapava do `except BaseAppException` das rotas) e a
converte explicitamente em `ConflictException`, fazendo rollback da
inserção inválida antes de propagar o erro. Como o endpoint público de
cadastro foi removido (item 2), esta correção protege o único caminho
de criação de usuário restante: `POST /admin/users`.

**Arquivos:** `app/services/user_service.py`.

**Impacto:** duas requisições concorrentes de criação de usuário com o
mesmo e-mail agora sempre resultam em um 409 previsível, nunca em 500
genérico.

### 11. Sem refresh token nem logout

**Solução:** `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (já existente em
`Settings`, mas nunca usado) passou a ser efetivamente utilizado.
Implementado fluxo completo de refresh token opaco, **persistido como
hash** (nunca em texto puro — mesma lógica de não guardar senhas em
claro) e com **rotação a cada uso** (o token antigo é revogado e um
novo é emitido, limitando o dano de um token vazado):
- `POST /auth/login` agora retorna `access_token` **e**
  `refresh_token`.
- `POST /auth/refresh` (novo): renova a sessão sem senha, usando um
  refresh token válido.
- `POST /auth/logout` (novo): revoga o refresh token informado.

**Arquivos modificados/criados:**
- `app/models/refresh_token.py` (novo)
- `alembic/versions/e2f3a4b5c6d7_...py` (novo) — cria a tabela `refresh_tokens`.
- `app/repositories/refresh_token_repository.py` (novo)
- `app/auth/refresh_token.py` (novo) — geração/hash do token opaco.
- `app/services/auth_service.py` — emissão/rotação/revogação.
- `app/routes/auth.py` — `/auth/refresh`, `/auth/logout`, `TokenResponse` com `refresh_token`.
- `app/auth/dependencies.py` — `get_auth_service` atualizado.
- `app/models/__init__.py` — registro do novo model.

**Impacto:** sessões podem ser renovadas sem exigir login por senha a
cada 30 minutos, com capacidade real de revogação (logout). **Mudança
de contrato de API:** `TokenResponse` ganha o campo obrigatório
`refresh_token` — clientes existentes que só leem `access_token`
continuam funcionando normalmente (campo adicional, não removido).

### 12. Backend sem healthcheck no Docker Compose

**Solução:** adicionado `healthcheck` ao serviço `backend` (usando o
`curl` já instalado no `Dockerfile` para esse fim) apontando para
`GET /api/v1/health`, e o serviço `frontend` passou a depender de
`backend` estar `service_healthy` (antes dependia apenas de
`started`).

**Arquivos:** `docker-compose.yml`.

**Impacto:** orquestração (local ou em produção) agora consegue saber
programaticamente quando a API está pronta para receber tráfego,
viabilizando rolling deploys e scripts de deploy automatizados.

---

## 🟢 Baixos

### 10. Arquivo de segredo real fora da proteção do `.gitignore`

**Solução:** o arquivo `backend/ - Copia.env` (com `X_CLIENT_SECRET`
real e `DEBUG=true`) foi **removido** do projeto entregue. O
`.gitignore` foi generalizado de um match exato (`backend/.env`) para
um padrão (`backend/*.env`, `backend/**/*.env`) que cobre qualquer
variante de nome terminada em `.env` dentro de `backend/`, prevenindo
recorrência do mesmo problema com outros nomes de arquivo.

**Arquivos:** `.gitignore`; remoção de `backend/ - Copia.env`.

**Impacto:** nenhum segredo real deve mais escapar da proteção do
`.gitignore`, independente do nome exato do arquivo. **Recomendação
operacional (fora do escopo de código):** como esse segredo circulou
fora do canal controlado, recomenda-se rotacionar o
`X_CLIENT_SECRET` do app do X junto ao provedor, por precaução.

### 14. README desatualizado

**Solução:** `README.md` reescrito para refletir o estado real do
projeto (autenticação, OAuth2 do X, posts, agendamento, admin,
observabilidade), removendo a descrição de "Etapa 2, apenas /health" e
adicionando instruções de bootstrap do catálogo de planos, criação do
primeiro administrador e funcionamento do agendamento/worker.

**Arquivos:** `README.md`.

### 15. Validação de e-mail fraca

**Solução:** `UserService._normalize_email` passou a validar o formato
do e-mail com uma expressão regular pragmática (usuário@domínio.tld),
em vez de checar apenas a presença de `"@"` na string. O schema
Pydantic (`str`) foi mantido como estava — a validação de formato
continua centralizada na camada de serviço, sem alterar o contrato de
entrada da rota.

**Arquivos:** `app/services/user_service.py`.

### 13. Módulo de custo por tipo de conteúdo é código morto

**Solução:** como o módulo (`app/domain/publication_cost.py`) não
causa nenhum bug hoje — simplesmente não é chamado por ninguém — e
reescrevê-lo para o fluxo real exigiria suporte a imagem/vídeo/link
que não existe em `CreatePostRequest` (fora do escopo desta correção),
foi adicionada uma nota explícita no topo do arquivo deixando claro que
ele **não está em uso** no fluxo real de publicação, prevenindo a
confusão de manutenção futura relatada na auditoria.

**Arquivos:** `app/domain/publication_cost.py`.

### 16. Enum de papel de usuário duplicado

**Solução:** como os dois enums (`app.models.enums.UserRole` e
`app.domain.enums.UserRole`) já eram reconciliados corretamente e
unificá-los exigiria alterar a modelagem SQLAlchemy existente (fora do
escopo desta correção, que evita refatorações não solicitadas), foi
adicionado um comentário cruzado em cada um apontando para o outro e
para o ponto exato da reconciliação manual
(`app.auth.dependencies`), reduzindo o risco de divergência futura
silenciosa.

**Arquivos:** `app/models/enums.py`, `app/domain/enums.py`.

---

## Resumo de impacto geral

- **Nenhuma correção anterior foi revertida.** A camada de domínio já
  madura (locks de concorrência, idempotência, criptografia, PKCE,
  constraints de banco) permanece intacta.
- **Mudanças de contrato de API:**
  - `POST /auth/register` **removido** (exigido pela regra de negócio
    definitiva: não há auto cadastro).
  - `TokenResponse` (`/auth/login`, `/auth/refresh`) ganha o campo
    `refresh_token` (aditivo).
  - Novas rotas: `POST /admin/plans/sync`,
    `POST /posts/{post_id}/schedule`, `DELETE /posts/{post_id}/schedule`,
    `POST /auth/refresh`, `POST /auth/logout`.
- **Nenhuma infraestrutura nova foi introduzida** (sem
  RabbitMQ/Celery/Kafka/Redis) — o agendamento usa o `apscheduler` já
  presente em `requirements.txt` rodando in-process, e a segurança
  contra duplicidade em múltiplos workers usa apenas recursos nativos
  do PostgreSQL já em uso (`SELECT ... FOR UPDATE SKIP LOCKED`).
- **Duas novas migrations Alembic**, ambas aditivas
  (`d1e2f3a4b5c6`: colunas em `scheduled_posts`;
  `e2f3a4b5c6d7`: tabela `refresh_tokens`), aplicadas com
  `alembic upgrade head`.

---

# CHANGELOG — Correções de alto, médio e baixo risco (rodada anterior)

Esta atualização conclui a segunda etapa da auditoria técnica do backend XHub, focando apenas nos problemas classificados como alto, médio e baixo que ainda precisavam de correção, sem mexer nas correções críticas já implementadas.

## Problemas corrigidos

- Proteção contra brute force em autenticação com rate limiting para as rotas de login e registro.
- Ajuste de configuração de deploy para evitar o uso de `--reload` e reduzir o risco operacional em produção.
- Hardenização do ambiente Docker Compose para não expor o banco publicamente e para permitir credenciais configuráveis via variáveis de ambiente.
- Verificação de que os demais itens de alto/médio/baixo já estavam cobertos pela implementação existente (listagem/desconexão de contas, refresh de token do X, sanitização do redirect OAuth, status HTTP 403 para acesso proibido, validação de UUID via Pydantic/FastAPI, senha limitada ao suporte do bcrypt, e arquivo de schema administrativo válido).

## Arquivos modificados

- [docker-compose.yml](docker-compose.yml)
- [Dockerfile](Dockerfile)
- [app/repositories/subscription_repository.py](app/repositories/subscription_repository.py)

## Resumo das alterações

- A middleware de rate limiting foi mantida e aplicada ao fluxo de autenticação sem alterar a arquitetura atual.
- O container do backend passou a iniciar com múltiplos workers e sem modo de reload, alinhando a execução a um cenário mais próximo de produção.
- O serviço de banco passou a ficar acessível somente via loopback local pelo host e a aceitar credenciais configuradas pelas variáveis de ambiente do compose.
- Um erro sintático em um repositório de assinaturas foi corrigido para preservar a compilação do backend.

## Impactos

- O fluxo de login/registro agora sofre limitação de tentativas, reduzindo risco de força bruta e abuso.
- O ambiente de execução ficou mais seguro e mais próximo de um deploy produtivo.
- Não houve mudança nas correções críticas já existentes no projeto.
