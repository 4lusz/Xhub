# XHub — Contexto técnico completo para IA

> Este arquivo é a fonte primária de contexto para qualquer IA (Claude ou
> outra) que for implementar, revisar ou depurar código neste repositório.
> Leia-o por inteiro antes de tocar em qualquer arquivo. Em caso de
> divergência entre este documento e o código, **o código é sempre a
> fonte da verdade** — atualize este arquivo, nunca assuma que ele está
> certo sem checar.
>
> Complementos especializados (não duplicados aqui): `docs/ROADMAP_MEDIA.md`
> (mídia), `docs/ROADMAP_PRIMEIRO_ACESSO.md` (primeiro acesso obrigatório),
> `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md` (Publicação Inteligente/Groq),
> `docs/ROADMAP_JITTER.md` (atraso entre publicações), `docs/ROADMAP_CUSTO_LINK.md`
> (custo diferenciado por conta para posts com link), `docs/ANALISE_ESCALABILIDADE.md`
> (análise de escalabilidade para clientes com muitas contas conectadas —
> scheduler, Groq, reuso de conexão HTTP), `docs/AUDITORIA_FUNCIONAL.md`
> (auditoria funcional completa — problemas reais encontrados e corrigidos,
> validações executadas), `docs/AUDITORIA_SEGURANCA.md` (auditoria completa
> de segurança — vulnerabilidades reais encontradas e corrigidas,
> dependências com CVE avaliadas, cobertura OWASP Top 10),
> `docs/ROADMAP_METRICAS.md` (métricas de desempenho por conta/post —
> tela "Resultados", coleta em background, detecção de anomalia de
> alcance), `docs/ROADMAP_COMPOSICAO_POST.md` (separação Fluxo 1/Fluxo 2
> — mesmo conteúdo compartilhado com Publicação Inteligente opcional vs.
> um tweet totalmente independente por conta, com mídia compartilhada ou
> individualizada). Cada um documenta a decisão técnica detalhada e a
> validação executada da sua respectiva funcionalidade.

## 1. Objetivo do XHub

XHub é um SaaS para gerenciar **múltiplas contas do X (Twitter)** por
usuário: conectar contas via OAuth2/PKCE, escrever um post uma única vez
e publicá-lo simultaneamente em uma ou mais contas conectadas, com
controle de acesso por planos/assinaturas administradas por um
administrador da plataforma (não há autoatendimento/self-signup).

Princípios de produto que orientam decisões técnicas:

- **Nunca publicar exatamente o mesmo texto em muitas contas ao mesmo
  tempo sem necessidade** — risco de bloqueio pela plataforma X. Daí a
  Publicação Inteligente (variação de texto) e o Jitter (variação de
  tempo).
- **Toda ação comercial (publicar, conectar conta) é validada contra
  plano/assinatura ANTES de qualquer efeito externo irreversível.**
- **O texto original do usuário nunca é sobrescrito** — `Post.text` é
  imutável; o que varia por conta é `PostAccount.rendered_text`.
- **Autoatendimento não existe** — toda conta (inclusive a primeira, via
  `app/scripts/create_admin.py`) nasce com senha temporária e
  `must_change_password=True`.

## 2. Arquitetura e camadas (backend)

Fluxo padrão, estrito, sem exceções:

```text
HTTP request
-> app/routes/*.py       (entrada HTTP: Depends, autorização, transação, response model)
-> app/auth/dependencies.py (monta services/clients via Depends)
-> app/services/*.py     (regra de negócio, orquestração, transação)
-> app/repositories/*.py (queries SQLAlchemy, sem regra de negócio)
-> app/models/*.py       (ORM, relacionamentos)
-> app/domain/*.py       (funções PURAS chamadas pelos services — sem I/O, sem SQLAlchemy, sem FastAPI)
```

Regras que **nunca devem ser quebradas** (ver também `.continue/rules/`):

- Rotas não contêm regra de negócio: apenas validam entrada, checam
  autorização via `Depends`, fazem commit/rollback e serializam a
  resposta. Uma exceção histórica conhecida: os schemas de `Post` ainda
  vivem dentro de `app/routes/post.py` em vez de `app/schemas/` — é uma
  divergência aceita, não repita o padrão em código novo (novas rotas
  devem usar `app/schemas/`, como `intelligent_publication.py` e
  `media.py` já fazem).
- Services recebem repositories e clientes externos **por injeção no
  construtor** (nunca instanciados internamente, nunca importados como
  singleton global) — isso é o que torna possível testar com dublês.
- `app/domain/` nunca importa SQLAlchemy, FastAPI, nem chama serviços
  externos. É onde vivem as regras de negócio puras e testáveis:
  `policies.py`, `media_rules.py`, `content_invariants.py`, `jitter.py`,
  `plans.py`, `publication_cost.py`, `contexts.py`, `enums.py`.
- Repositories nunca commitam — commit/rollback é responsabilidade da
  rota (ou do worker do scheduler), que é quem sabe o escopo real da
  transação.
- `AuditLog` é append-only: `AuditLogRepository` sobrescreve
  `update`/`delete`/`delete_by_id` para sempre levantar `ConflictException`.
- Chamada externa (X API, Groq) fica sempre encapsulada em um cliente
  dedicado (`XOAuthClient`, `GroqClient`) — nunca espalhada em rota ou
  service genérico.
- IDs são sempre UUID. Toda mudança de schema exige migration Alembic
  (nunca alterar tabela via SQL manual fora de migration).
- Mensagens de erro voltadas ao usuário ficam em português, estilo já
  usado no projeto inteiro.
- Enums persistidos em banco ficam em `app/models/enums.py` (native
  Postgres enum). **Atenção a uma divergência conhecida:** existe um
  segundo `UserRole`/`SubscriptionStatus` em `app/domain/enums.py`,
  mantido manualmente sincronizado com o de `models/enums.py` via
  `_to_user_context` em `dependencies.py`. É dívida técnica intencional
  (mantém `domain/` livre de importar `models/`), não um bug — mas se
  você adicionar um valor a um dos dois, adicione ao outro também.

## 3. Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (síncrono, sem
`async def` em nenhuma rota — todo I/O externo usa `httpx` síncrono),
Alembic, PostgreSQL 16, Pydantic v2, JWT (HS256), OAuth2/PKCE,
APScheduler (`BackgroundScheduler` in-process), `cryptography` (Fernet),
`passlib`/bcrypt, Groq (LLM), `pytest`.

**Frontend:** React 19, TypeScript, Vite 6, TailwindCSS 3 +
shadcn/ui (Radix UI primitives), React Router 7, TanStack Query 5,
Axios, Zustand (+ `persist`), React Hook Form + Zod, `@ffmpeg/ffmpeg`
(ffmpeg.wasm, self-hosted), `react-easy-crop`, Framer Motion.

**Infra:** Docker Compose (3 serviços: `db`, `backend`, `frontend`),
sem broker de fila (scheduler é in-process), sem cache externo (Redis
etc. — cache da Publicação Inteligente é em memória, por processo).

## 4. Estrutura de pastas

```text
xhub/
├── docker-compose.yml
├── README.md
├── claude.md                       # este arquivo
├── docs/                           # especificações + estado implementado por feature
│   ├── ROADMAP_MEDIA.md
│   ├── ROADMAP_PRIMEIRO_ACESSO.md
│   ├── ROADMAP_PUBLICACAO_INTELIGENTE.md
│   └── ROADMAP_JITTER.md
├── .continue/                      # base de conhecimento para Continue.dev (IDE)
│   ├── context/XHUB_CONTEXT.md     # espelho resumido deste arquivo
│   ├── context/ROADMAP.md          # estado implementado/planejado, vivo
│   └── rules/                      # regras curtas e prescritivas para o Continue
├── backend/
│   ├── alembic/versions/           # uma migration por mudança de schema
│   └── app/
│       ├── main.py                 # bootstrap: lifespan, middleware, routers
│       ├── config/settings.py      # pydantic-settings, ÚNICA fonte de env vars
│       ├── database/               # engine, session, base declarativa
│       ├── models/                 # ORM: User, TwitterAccount, Plan, Subscription,
│       │                           #   Post, PostAccount, PostMedia, ScheduledPost,
│       │                           #   OAuthSession, AuditLog, JitterSettings, RefreshToken,
│       │                           #   AccountMetricSnapshot, PostMetricSnapshot
│       ├── domain/                 # regras puras (ver seção 2)
│       ├── repositories/           # acesso a dados, sem regra de negócio
│       ├── services/               # regra de negócio e orquestração
│       ├── schemas/                # Pydantic request/response (parcial — ver nota na seção 2)
│       ├── routes/                 # FastAPI routers
│       ├── auth/                   # JWT, hashing, refresh token, dependencies de papel
│       ├── oauth/                  # PKCE, XOAuthClient (HTTP puro), XOAuthService (orquestração)
│       ├── integrations/           # GroqClient
│       ├── core/                   # exceptions, crypto (Fernet), media_storage, logging, security
│       ├── middleware/             # rate limit, request-id de correlação,
│       │                           #   headers de segurança, limite de corpo
│       ├── scheduler.py            # worker in-process de agendamento
│       └── scripts/create_admin.py # bootstrap do primeiro admin
└── frontend/
    └── src/
        ├── routes/                 # ProtectedRoute, AdminRoute, ClientOnlyRoute (guards)
        ├── layouts/                # AuthLayout, DashboardLayout
        ├── pages/                  # uma página por rota
        ├── components/             # admin/, dashboard/, posts/, intelligent-publication/,
        │                           #   accounts/, layout/, common/, ui/ (shadcn)
        ├── hooks/                  # TanStack Query por domínio
        ├── services/                # axios calls por domínio (base HTTP em services/api.ts)
        ├── stores/authStore.ts     # Zustand: tokens + mustChangePassword
        ├── types/                  # interfaces TS por domínio
        └── lib/                    # format, imageCrop, mediaRules, utils
```

## 5. Entidades principais

| Model | Tabela | Papel |
|---|---|---|
| `User` | `users` | Conta da plataforma. `role` (client/admin), `is_blocked`, `must_change_password`. |
| `TwitterAccount` | `twitter_accounts` | Conta do X conectada via OAuth2. Tokens Fernet-criptografados. Único `(user_id, twitter_user_id)`. |
| `Plan` | `plans` | Catálogo comercial: `max_accounts`, `max_posts_month`, `price`. Sincronizado de `app/domain/plans.py` no startup. |
| `Subscription` | `subscriptions` | Assinatura do usuário. Só uma `ACTIVE` por usuário (índice parcial único). `used_posts`/`extra_posts` controlam saldo. |
| `Post` | `posts` | Texto original (`text`, imutável) + status agregado. |
| `PostAccount` | `post_accounts` | Fan-out por conta: uma linha por `(Post, TwitterAccount)`. `status`, `x_post_id`, `error_message` (admin-only), `rendered_text` (texto final da Publicação Inteligente). |
| `PostMedia` | `post_media` | Imagem/gif/vídeo anexado a um post — idêntico para todas as contas de destino. `post_id` nullable até anexação. |
| `ScheduledPost` | `scheduled_posts` | Agendamento 1:1 com `Post`. `executed`, `attempts`, `last_error`. |
| `OAuthSession` | `oauth_sessions` | Estado PKCE efêmero (10 min), single-use, sem relação com `TwitterAccount`. |
| `AuditLog` | `audit_logs` | Trilha administrativa, append-only, sem `updated_at`. |
| `JitterSettings` | `jitter_settings` | Tabela singleton (sempre 1 linha): `min_seconds`/`max_seconds` do Jitter, editável pelo admin. |
| `RefreshToken` | `refresh_tokens` | Token opaco, armazenado só como hash SHA-256. Rotação a cada uso. |
| `AccountMetricSnapshot` | `account_metric_snapshots` | Série histórica de seguidores por conta, append-only. Coletada em background (ver seção 12-A). |
| `PostMetricSnapshot` | `post_metric_snapshots` | Série histórica de impressões/curtidas/respostas/republicações por `PostAccount`, append-only. `twitter_account_id` denormalizado. |

## 6. Fluxo de autenticação

1. `POST /auth/login` (form-encoded, `OAuth2PasswordRequestForm`) — sempre
   aceito mesmo com senha temporária; retorna `access_token` (JWT, 30 min),
   `refresh_token` (opaco, 7 dias) e `must_change_password`.
2. Todo endpoint protegido depende de `get_current_user` (ou
   `get_current_client`/`get_current_admin`, que empilham por cima):
   decodifica JWT → carrega `User` → `ensure_user_not_blocked` (403) →
   `ensure_password_change_not_required` (**428**, não 401/403 — ver
   seção 9). A única exceção é `POST /auth/change-password`, que usa
   `get_current_user_for_password_change` (pula o gate de 428
   deliberadamente, senão o usuário nunca conseguiria trocar a senha).
3. `POST /auth/refresh` roda **rotação**: valida o refresh token
   apresentado (existe, não revogado, não expirado) → revoga-o →
   emite um par novo. Reuso de um token já revogado falha (sinaliza
   possível vazamento).
4. `POST /auth/logout` revoga o refresh token informado (o access token
   permanece tecnicamente válido até expirar naturalmente — é stateless
   por design).
5. Tokens OAuth do X (`TwitterAccount.access_token`/`refresh_token`) são
   cifrados em repouso com Fernet (`app/core/crypto.py`), nunca em texto
   puro no banco.

No frontend: `authStore` (Zustand + `persist`, localStorage) guarda
`accessToken`/`refreshToken`/`mustChangePassword`. O interceptor Axios
(`services/api.ts`) injeta `Authorization: Bearer`, faz refresh
single-flight em 401 (deduplica requisições paralelas via
`refreshPromise` módulo-level), e trata 428 como rede de segurança
(força `/first-access`) complementando — não substituindo — o gate de
roteamento síncrono em `ProtectedRoute`.

## 7. Fluxo OAuth (conexão de conta do X)

1. `GET /oauth/x/login` (autenticado) → `XOAuthService.build_login_url`:
   valida quota de contas conectáveis (`ensure_can_connect_account`,
   locked) **antes** de iniciar o fluxo, gera `code_verifier`/`code_challenge`/
   `state` (PKCE), persiste `OAuthSession` no Postgres (não em memória —
   necessário para corretude com múltiplos workers/réplicas do backend),
   TTL de 10 minutos.
2. `GET /oauth/x/callback` (público, chamado pelo X) → `complete_callback`:
   consome a sessão (deletada imediatamente, mesmo se expirada — evita
   replay), troca `code` por tokens, busca o perfil autenticado no X,
   revalida quota só se for conta nova, faz upsert via
   `TwitterAccountService.save_connected_account` (cifra os tokens).
   Redireciona (302) para `FRONTEND_URL/accounts` com
   `?oauth=x&status=connected|error` (nunca para a raiz do frontend --
   desde que o site público de marketing passou a ocupar `/`, a raiz
   não está mais dentro do layout autenticado que exibe o retorno ao
   usuário, ver `useOAuthCallbackFeedback`).
3. `XOAuthClient` é HTTP puro (sem DB/regra de negócio): troca de código,
   refresh de token, perfil do usuário, publicação de tweet, upload de
   mídia chunked (INIT/APPEND/FINALIZE/STATUS, endpoint v2 nativo).

## 8. Fluxo de publicação (`PostService.publish_post`) — o coração do sistema

Ordem exata dentro de `publish_post`, na qual cada nova feature (Jitter,
Publicação Inteligente, mídia) foi inserida sem reordenar o que já
existia:

1. Carrega `PostAccount`s do post; remove da tentativa os já `PUBLISHED`
   (idempotência: nunca republica um sucesso anterior).
2. Calcula o custo por conta (`credits_per_account_for_post(post.text)`
   — 15 créditos/conta se `Post.text` contiver um link, 1 crédito/conta
   caso contrário; ver `docs/ROADMAP_CUSTO_LINK.md`) e valida assinatura
   ativa e saldo suficiente **para todas** as contas que ainda serão
   tentadas nesta chamada, no custo real total (`contas pendentes *
   créditos por conta`) — antes de qualquer chamada externa
   irreversível.
3. Para cada conta pendente/falha, na ordem (`enumerate`):
   a. **Jitter**: se `account_index > 0` (nunca antes da primeira conta
      da chamada), `JitterService.apply_delay(...)` — sorteia um atraso
      independente (`uniform(min, max)`, valores configuráveis pelo
      admin em `jitter_settings`) e bloqueia (`time.sleep`) antes de
      seguir para esta conta. Uma conta sozinha nunca sofre atraso.
   b. Obtém/renova o access token do X para essa conta
      (`_get_valid_access_token`, refresh automático se expirado).
   c. Se há mídia anexada, faz upload dela para o X **desta conta
      especificamente** (`XOAuthClient.upload_media` — cada conta tem
      sua própria biblioteca de mídia no X, mesmo arquivo local
      reenviado por conta).
   d. Publica o tweet com `post_account.rendered_text or post.text`
      (texto da Publicação Inteligente se existir, senão o original) +
      `media_ids` se houver.
   e. Marca o `PostAccount` como `PUBLISHED` (com `x_post_id`) ou
      `FAILED` (com `error_message`, visível só para admin); em caso de
      sucesso, consome `credits_per_account` créditos do saldo da
      assinatura (1 ou 15, nunca um valor fixo).
4. Atualiza `Post.status` agregado (`PUBLISHED` se todas as contas
   tentadas tiveram sucesso, senão `FAILED`).

Este é o mesmo método chamado tanto por `POST /posts/{id}/publish`
quanto pelo worker do scheduler — **não existe um segundo caminho de
publicação**. Qualquer nova regra de publicação deve entrar aqui, nesta
ordem, sem duplicar lógica em outro lugar.

## 9. Primeiro acesso obrigatório

- Toda conta nasce com `must_change_password=True` (inclusive o
  primeiro admin, via `create_admin.py`).
- Enquanto `True`, **nenhuma** rota protegida além de
  `POST /auth/change-password` responde (nem rota de admin, nem de
  cliente — sem exceção por papel), porque o gate vive em
  `get_current_user`, herdado por `get_current_client`/`get_current_admin`.
- HTTP **428** (não 401/403) foi escolhido deliberadamente: 403 já
  significa "acesso negado" (bloqueado/papel errado) no projeto; reusar
  esse código obrigaria o frontend a inspecionar a mensagem de erro
  (frágil) para diferenciar os dois casos.
- Completar a troca (ou uma redefinição administrativa) revoga **todos**
  os refresh tokens do usuário — qualquer sessão antiga precisa logar de
  novo.
- Redefinição administrativa (`POST /admin/users/{id}/reset-password`):
  gera senha temporária aleatória (nunca escolhida pelo admin, nunca vista
  duas vezes), reabre o ciclo de primeiro acesso.
- Detalhe completo e validação em `docs/ROADMAP_PRIMEIRO_ACESSO.md`.

## 10. Publicação Inteligente (variação de texto via Groq)

Regra por quantidade de contas selecionadas (`app/domain/policies.py`,
compartilhado entre `PostService` e `AIContentVariationService` —
constantes `OPTIONAL_VARIATION_MAX_ACCOUNTS=4`,
`MANDATORY_VARIATION_ACCOUNT_THRESHOLD=5`):

- **1 conta**: sempre texto original; Groq nunca é chamada.
- **2–4 contas**: variação **opcional** (frontend ativa por padrão, com
  aviso recomendando o uso). Se a Groq falhar, cai silenciosamente para
  o texto original — nunca bloqueia a publicação.
- **5+ contas**: variação **obrigatória**, sem fallback para texto
  igual. Se a Groq estiver indisponível ou não gerar variações válidas
  suficientes, a criação do post é interrompida **antes de qualquer
  chamada ao X** — usuário pode tentar de novo, salvar como rascunho ou
  reagendar.

Fluxo: `POST /intelligent-publication/preview` (nunca cria `Post`) →
`AIContentVariationService.generate_preview` decide a estratégia →
consulta cache em memória (chave = hash de texto+contas+modelo+versão do
prompt, TTL configurável) → chama `GroqClient` (nunca OpenAI — requisito
de produto explícito) só para o que faltar → valida cada variação
retornada com `app/domain/content_invariants.py` (URLs, hashtags,
@menções, emojis e CTA devem ser preservados **exatamente**; qualquer
variação que altere um desses é descartada, nunca corrigida
silenciosamente) → retorna um preview editável por conta. A confirmação
reaproveita `POST /posts` normal, com `rendered_texts` por conta —
`PostService.create_post` **revalida tudo de novo** (obrigatoriedade,
invariantes, duplicidade), e `publish_post` valida uma **terceira vez**
imediatamente antes de chamar o X (defesa em profundidade contra dados
antigos ou edição direta no banco).

`Post.text` nunca é sobrescrito; `PostAccount.rendered_text` guarda o
texto final por conta (`NULL` = usa o original no publish).

Detalhe completo, prompt exato e validação em
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`.

## 11. Upload e edição de mídia

- Upload (`POST /media/upload`, multipart) acontece **antes** do post
  existir — o arquivo fica em disco (`media_storage/{user_id}/{uuid}{ext}`,
  streaming, nunca todo em memória) com `PostMedia.post_id=NULL` até ser
  anexado via `POST /posts` (`media_ids`).
- Regras (`app/domain/media_rules.py`, espelhadas no frontend em
  `lib/mediaRules.ts` só para feedback instantâneo — backend é a única
  fonte de verdade): máx. 4 itens/post; imagem 5MB, gif 15MB, vídeo
  512MB; vídeo ou gif devem estar sozinhos no post; até 4 imagens podem
  se combinar.
- Mídia é **idêntica em todas as contas de destino** — só o texto varia
  (Publicação Inteligente nunca toca em mídia).
- Publicação com mídia: cada conta de destino recebe seu próprio upload
  para o X (`XOAuthClient.upload_media`, protocolo v2 nativo
  INIT/APPEND/FINALIZE + polling de STATUS para gif/vídeo assíncrono) —
  mesmo arquivo local, reenviado uma vez por conta, porque cada conta
  tem sua própria biblioteca de mídia no X.
- Edição de mídia é **inteiramente client-side** (decisão explícita do
  usuário — nenhum processamento novo no backend): crop/zoom/rotação de
  imagem via `react-easy-crop` + canvas (`lib/imageCrop.ts`); corte real
  de vídeo via `ffmpeg.wasm` (`-c copy`, sem recodificar — mais rápido,
  ao custo de encaixar no keyframe mais próximo). O core do ffmpeg
  (~30MB) é self-hosted em `public/ffmpeg/` (nunca CDN de terceiros).
  `originalFile` nunca é sobrescrito — reeditar sempre parte do arquivo
  original, evitando degradar qualidade a cada edição sucessiva.
- Excluir um post apaga os arquivos do disco **antes** de apagar as
  linhas do banco (cascade do Postgres não toca o filesystem).

Detalhe completo e validação (incluindo teste real contra a API do X
que confirmou o protocolo v2 de upload) em `docs/ROADMAP_MEDIA.md`.

## 12. Scheduler (agendamento)

`APScheduler` `BackgroundScheduler` in-process (sem broker externo),
`max_instances=1` + `coalesce=True` (nunca roda duas execuções
sobrepostas; execuções perdidas colapsam em uma só, nunca acumulam
backlog). A cada `SCHEDULER_INTERVAL_SECONDS` (30s padrão):

1. `SELECT ... FOR UPDATE SKIP LOCKED` sobre `scheduled_posts` vencidos
   (`ScheduledPostRepository.list_due_for_update_skip_locked`) — é isso
   que torna seguro rodar múltiplas réplicas do backend ao mesmo tempo:
   cada processo só enxerga agendamentos que nenhum outro processo já
   tem travado.
2. Para cada post reivindicado, chama **o mesmo** `PostService.publish_post`
   usado pela rota manual — não existe lógica de publicação duplicada.
3. Marca `executed=True`/`attempts+=1` e libera o lock.
4. Erro inesperado vira `ScheduledPost.last_error` (truncado); falha
   esperada por conta já vive em `PostAccount.error_message`.

O Jitter atua **dentro** de `publish_post`, então uma tick do scheduler
com muitas contas pode demorar mais — consequência esperada e aceita
(analisada explicitamente; não compromete `max_instances=1`/`coalesce`,
só atrasa proporcionalmente o início da próxima tick).

O mesmo `BackgroundScheduler` também roda `collect_account_and_post_metrics`
(ver `docs/ROADMAP_METRICAS.md`) — job independente, intervalo próprio
(`METRICS_COLLECTION_INTERVAL_SECONDS`, bem mais espaçado que o de
posts, já que cada leitura tem custo real na API do X), sem nenhum
worker/broker adicional.

## 13. Jitter (atraso natural entre publicações)

Objetivo: publicações em múltiplas contas do mesmo post não acontecem
no mesmo instante, reduzindo o padrão automatizado percebido pela
plataforma X.

- Atraso só existe **entre** contas, nunca antes da primeira; conta
  única nunca tem atraso (`account_index > 0` em `publish_post`, ver
  seção 8).
- `app/domain/jitter.py::sample_jitter_delay_seconds(min, max)` — função
  pura, `random.uniform`, uma amostra independente por chamada (nunca
  reaproveita valor).
- `JitterService.apply_delay` é o único lugar que efetivamente dorme
  (`time.sleep`) e loga (estruturado, sem expor o valor exato ao
  usuário final — só para debug/auditoria técnica).
- Configuração (`min_seconds`/`max_seconds`) vive na tabela singleton
  `jitter_settings` (não em `.env`/`Settings`, porque settings só são
  lidas uma vez no boot via `@lru_cache` — mudança do admin precisa
  valer sem reiniciar o processo). Editável via
  `GET`/`PATCH /admin/jitter-settings` (tela dedicada "Jitter" no
  painel admin). Teto de segurança `JITTER_MAX_ALLOWED_SECONDS` (120s
  padrão) impede um valor absurdo travar a chamada síncrona de
  publicação.
- Detalhe completo e validação em `docs/ROADMAP_JITTER.md`.

## 14. Painel administrativo

Tudo sob `/admin/*` (backend) / `/admin/*` (frontend), protegido por
`get_current_admin` (backend) e `AdminRoute` (frontend). Seções:
Usuários (criar, bloquear/desbloquear, trocar papel, redefinir senha),
Assinaturas (renovar, bloquear, expirar, adicionar/remover posts
extras — via dialog por usuário, não tela própria), Planos (editar
preço/limites, resincronizar catálogo), Publicações (visão somente
leitura entre usuários, filtro por status — nunca expõe o texto do
post, só metadados/erro), Auditoria (log append-only, paginado), Jitter
(min/max segundos). `AdminDashboardPage` mostra estatísticas agregadas.

**Separação de rotas por papel (frontend, área recente):**
`ClientOnlyRoute` redireciona admin → `/admin` sempre que ele tenta
acessar `/dashboard`, `/accounts`, `/posts`, `/posts/new`, `/scheduled`
ou `/results` (contas admin nunca recebem `Subscription`, então essas
telas terminariam em erro para elas). `AdminRoute` faz o espelho:
cliente tentando `/admin/*` volta para `/dashboard`. `Sidebar.tsx`
renderiza um array de navegação inteiramente diferente por papel
(`adminNav` vs. `primaryNav`), nunca mesclado. `/profile`, `/settings` e
`/first-access` são comuns aos dois papéis.

**Site público de marketing (`/`, `/sobre`, `/contato`, `/faq`,
`/privacidade`, `/termos`):** rotas totalmente públicas, fora de
`ProtectedRoute`, servidas por `MarketingLayout` (header + footer
próprios, sem sidebar) — nunca dependem de sessão nem tocam nenhum
endpoint autenticado. `/` deixou de ser a home autenticada (que agora
vive em `/dashboard`) para se tornar a landing page pública — decisão
tomada ao construir essa área, replicando o padrão comum de SaaS
(domínio raiz = marketing, `/dashboard` = produto). Não existe
cadastro público: o CTA "Criar conta" leva para `/contato`
(`xhubplatform@gmail.com`), refletindo a regra de negócio real (toda
conta é criada por um administrador).

## 15. Autorização — papéis e dependencies

- `UserRole`: `client` | `admin`.
- `get_current_user`: qualquer usuário autenticado, não bloqueado, sem
  troca de senha pendente.
- `get_current_client`: acima + papel `client`.
- `get_current_admin`: acima + papel `admin`.
- Posse de recurso (ex.: um post pertence ao usuário autenticado) é
  checada **na rota**, não delegada a um dependency genérico — ver
  `app/routes/post.py`.

## 16. Convenções de código

- Tipagem explícita nos limites públicos de classes/funções (Python).
- Todo model SQLAlchemy herda `Base` e, exceto `AuditLog` (append-only,
  sem `updated_at`), `TimestampMixin`.
- Exceções esperadas de domínio/aplicação sempre via
  `app/core/exceptions.py` (`BaseAppException` e subclasses:
  `ValidationException`→422, `NotFoundException`→404,
  `ConflictException`→409, `UnauthorizedException`→401,
  `ForbiddenException`→403, `PasswordChangeRequiredException`→428,
  `BadRequestException`→400, `ServiceUnavailableException`→503). Nunca
  deixe uma exceção genérica do Python vazar de um service — o handler
  global em `main.py` converte qualquer coisa não mapeada em 500 sem
  detalhe interno, o que é intencional para não vazar stack trace, mas
  esconde bugs se você depender disso no lugar de tratar o erro
  corretamente.
- Nunca ler `os.environ` diretamente — sempre `app.config.settings.settings`.
- Frontend: chamadas HTTP centralizadas em `services/*.ts`; tipos
  compartilhados em `types/*.ts`; hooks TanStack Query para toda
  consulta/mutação reutilizável; estados de loading/erro/sucesso sempre
  tratados nos componentes que consomem API; nunca criar tela/fluxo
  fictício sem endpoint correspondente.
- Logging estruturado (JSON, uma linha por evento) com `request_id` de
  correlação (`X-Request-ID`) em toda a aplicação backend.

## 17. Lacunas e dívidas técnicas conhecidas (não "corrigir por conta própria" sem alinhar antes)

- `AuditAction.SUBSCRIPTION_CREATED`, `TWITTER_ACCOUNT_CONNECTED`,
  `TWITTER_ACCOUNT_DISCONNECTED` e `OTHER` existem no enum mas **nunca
  são de fato registrados** — criar assinatura via `POST /admin/users`,
  conectar e desconectar conta do X não geram entrada de auditoria hoje,
  apesar do enum sugerir que deveriam.
- `app/domain/enums.py` duplica `UserRole`/`SubscriptionStatus` de
  `app/models/enums.py` (ver seção 2) — sincronização manual, não
  automática.
- Suíte `pytest` (`backend/tests/`) é fina: 4 arquivos, cobertura de
  wiring/serialização de poucos endpoints, sem teste automatizado para
  `PostService.publish_post`, `AIContentVariationService`,
  `JitterService`, scheduler, ou as funções puras de `app/domain/`
  (validadas manualmente/via script descartável a cada feature, não por
  suíte automatizada). Há uma falha pré-existente e não relacionada,
  estável há várias features:
  `test_get_subscription_returns_subscription_for_admin` em
  `test_routes_admin.py` (dublê desatualizado de
  `SubscriptionService.to_domain_context`).
- Schemas de `Post`/`ScheduledPost` ainda vivem dentro de
  `app/routes/post.py`, não em `app/schemas/` (padrão usado por feature
  mais nova, como `media`/`intelligent_publication`).
- Nenhuma detecção de gif animado vs. estático (tudo `image/gif` é
  tratado como categoria "gif", a mais restritiva — sempre seguro, nunca
  incorreto, só potencialmente mais restritivo que o necessário).
- Cache da Publicação Inteligente é em memória, por processo — não
  compartilhado entre réplicas/workers (mesmo trade-off aceito do rate
  limiter). Nunca serve dado errado (a chave inclui todo o contexto
  relevante), só tem uma taxa de acerto menor com múltiplos processos.
- Coleta de métricas (`docs/ROADMAP_METRICAS.md`) segue a documentação
  oficial da API do X para o formato de `organic_metrics`/
  `public_metrics`, mas ainda não foi validada contra uma coleta real
  em produção (sem conta reconectada com posts recentes disponível no
  momento da implementação) — confirmar na primeira coleta real, mesmo
  princípio já registrado para o upload de mídia antes de ser validado.
- Detecção de anomalia de alcance (`app.domain.metrics.detect_reach_anomaly`)
  não normaliza por dia da semana/horário — pode gerar falso-positivo
  em padrões semanais previsíveis (ex.: toda segunda de manhã). Aceito
  para a primeira versão; refinamento possível, não crítico.
- Não há cota de armazenamento por usuário nem limpeza automática de
  `PostMedia` nunca anexada a nenhum post (`post_id IS NULL`
  indefinidamente) — um usuário autenticado pode acumular arquivos
  órfãos ao longo do tempo até o limite de disco do servidor. Mitigado
  parcialmente por rate limiting em `POST /media/upload` (ver
  `docs/AUDITORIA_SEGURANCA.md`); uma cota de fato exigiria um campo/
  política nova em `Plan`/`Subscription` — funcionalidade nova, não
  implementada.

Ao encontrar qualquer uma dessas situações, trate como já entendida e
documentada — não é necessário "descobrir" de novo nem propor correção
sem que o usuário peça explicitamente.
