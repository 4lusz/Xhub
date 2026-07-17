# XHub - Contexto permanente para IA de desenvolvimento

Este documento e contexto tecnico permanente para Continue.dev. Ele descreve o
estado observado no codigo do projeto em 2026-07-16. E um resumo; o contexto
completo e detalhado vive em `claude.md` (raiz do repositorio) -- leia-o antes
de qualquer tarefa nao trivial. O README.md (raiz) e o documento
orientado a produto/operacao.

## Produto

XHub e um SaaS para gerenciar multiplas contas do X (Twitter) por usuario,
publicar posts em uma ou mais contas conectadas via OAuth2 e controlar uso por
planos/assinaturas. Nao ha autocadastro: toda conta e criada por um
administrador.

## Estado atual observado

Backend implementado:

- FastAPI com prefixo `/api/v1`, logging estruturado, `request_id` de
  correlacao, handler global de excecoes.
- Autenticacao por JWT (access token) + refresh token opaco com rotacao.
- Primeiro acesso obrigatorio (`must_change_password`, HTTP 428) -- ver
  `docs/ROADMAP_PRIMEIRO_ACESSO.md`.
- Usuarios com roles `client` e `admin`; criacao administrativa com
  assinatura explicita.
- Planos e assinaturas com limites de contas e posts mensais; posts extras.
- Auditoria administrativa (append-only).
- OAuth2 do X com PKCE; sessao OAuth persistida no Postgres (nao em memoria).
- Multiplas contas do X por usuario, com foto de perfil e `@username` como
  identificador principal.
- Criacao, listagem, consulta, exclusao, agendamento e publicacao de posts.
- Fan-out de publicacao por conta usando `PostAccount`, com `rendered_text`
  proprio por conta.
- Refresh automatico de access token do X quando expirado.
- Publicacao via API oficial do X (`POST /2/tweets`), com upload de midia
  (imagem/gif/video) por conta via protocolo v2 nativo (INIT/APPEND/
  FINALIZE/STATUS).
- Upload/armazenamento de midia em disco (`app/core/media_storage.py`),
  validacao de tipo/tamanho/combinacao (`app/domain/media_rules.py`) -- ver
  `docs/ROADMAP_MEDIA.md`.
- Publicacao Inteligente: variacao de texto por conta via Groq
  (`AIContentVariationService` + `GroqClient`), obrigatoria com 5+ contas,
  opcional com 2-4, nunca usada com 1 conta -- ver
  `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`.
- Jitter: atraso aleatorio configuravel pelo admin entre publicacoes em
  contas diferentes de um mesmo post -- ver `docs/ROADMAP_JITTER.md`.
- Scheduler in-process (APScheduler) com `FOR UPDATE SKIP LOCKED`, seguro
  para multiplas replicas do backend.

Frontend implementado:

- Autenticacao completa (login, refresh silencioso, logout, primeiro acesso
  obrigatorio com tela dedicada).
- Roteamento com guards por papel: `ProtectedRoute` (autenticacao +
  primeiro acesso), `ClientOnlyRoute` (redireciona admin -> `/admin`),
  `AdminRoute` (redireciona cliente -> `/`). Sidebar renderiza navegacao
  totalmente diferente por papel.
- Telas de cliente: Dashboard, Contas do X, Posts (historico + criacao +
  agendamento), Perfil, Configuracoes.
- Compositor de post com upload/edicao de midia 100% client-side
  (crop/zoom/rotacao de imagem via `react-easy-crop`; corte de video via
  `ffmpeg.wasm`, self-hosted) e fluxo completo de Publicacao Inteligente
  (modal de preview/edicao por conta).
- Painel administrativo completo: usuarios, planos, assinaturas (por
  usuario), publicacoes (somente leitura, sem expor texto), auditoria,
  Jitter, estatisticas agregadas.
- Axios configurado em `frontend/src/services/api.ts` com interceptors de
  refresh token (single-flight) e tratamento de 428.

## Arquitetura backend

Camadas principais:

- `routes`: entrada HTTP, Depends, autorizacao, commit/rollback, response models.
- `services`: regras de negocio e orquestracao de repositories/clientes externos.
- `repositories`: queries SQLAlchemy e persistencia.
- `models`: SQLAlchemy ORM e relacionamentos.
- `domain`: regras puras, policies, dataclasses e enums independentes de framework.
- `auth`: JWT, password hashing, refresh token e dependencies de usuario atual.
- `oauth`: OAuth2/PKCE, cliente HTTP do X e service de conexao de contas.
- `integrations`: cliente HTTP da Groq.
- `config`: settings centralizados via pydantic-settings.
- `core`: excecoes, criptografia, storage de midia, logging estruturado.

Fluxo padrao:

```text
HTTP request
-> app.routes.*
-> Depends em app.auth.dependencies
-> app.services.*
-> app.repositories.*
-> app.models.*
-> database session
```

Detalhe completo de cada camada, convencoes e decisoes arquiteturais: ver
`claude.md`.

## Banco de dados

Persistencia usa PostgreSQL, SQLAlchemy 2.0 e Alembic.

Models principais: `User`, `TwitterAccount`, `Plan`, `Subscription`, `Post`,
`PostAccount` (com `rendered_text`, `x_post_id`, `error_message`),
`PostMedia`, `ScheduledPost`, `OAuthSession`, `AuditLog`, `JitterSettings`
(tabela singleton), `RefreshToken`.

Padroes:

- IDs sao UUID.
- `TimestampMixin` fornece `created_at` e `updated_at` (exceto `AuditLog`,
  append-only, sem `updated_at`).
- Mudancas de schema exigem migration Alembic.
- Relacionamentos usam cascade quando o agregado deve apagar dependentes.

## Autenticacao e autorizacao

- Login gera JWT (access token) + refresh token opaco (hash SHA-256
  persistido, rotacao a cada uso).
- `get_current_user`: decodifica token, bloqueia usuario bloqueado
  (`ensure_user_not_blocked`) e exige troca de senha concluida
  (`ensure_password_change_not_required`, HTTP 428).
- `get_current_user_for_password_change`: usado exclusivamente por
  `POST /auth/change-password`, pula o gate de 428.
- `get_current_admin`/`get_current_client`: empilham papel sobre
  `get_current_user`.
- Rotas administrativas dependem de `get_current_admin`.

## Assinaturas e limites

Regras atuais:

- Usuario precisa de assinatura ativa para publicar ou conectar conta.
- Assinatura e validada com lock `FOR UPDATE` antes de qualquer efeito
  externo irreversivel.
- O saldo precisa cobrir todas as contas que ainda serao publicadas na
  chamada.
- O consumo (`used_posts`) ocorre por conta publicada com sucesso.
- Contas ja publicadas com sucesso nao sao reprocessadas.
- Limite de contas conectadas vem do plano da assinatura.
- Contas admin nao recebem assinatura por design.

## Publicacao atual

Fluxo de `POST /posts/{post_id}/publish` (identico ao usado pelo scheduler):

1. Remove da tentativa contas ja `PUBLISHED`.
2. Valida assinatura ativa e saldo antes de qualquer chamada externa.
3. Para cada conta pendente/falha (em ordem):
   - aplica o atraso do Jitter, exceto na primeira conta da chamada;
   - obtem/renova token valido;
   - envia midia anexada para o X, se houver, especificamente para essa conta;
   - chama `XOAuthClient.publish_post` usando
     `PostAccount.rendered_text or Post.text`;
   - marca `PostAccount` como `PUBLISHED` ou `FAILED`.
4. Atualiza o `Post.status` agregado.

`Post.text` e sempre o texto original; `PostAccount.rendered_text` e o texto
final por conta (gerado pela Publicacao Inteligente ou editado manualmente).

## Integracoes externas

X API:

- Autorizacao: `https://x.com/i/oauth2/authorize`
- Token: `https://api.x.com/2/oauth2/token`
- Usuario autenticado: `https://api.x.com/2/users/me`
- Publicacao: `https://api.x.com/2/tweets`
- Upload de midia (v2 nativo): `https://api.x.com/2/media/upload` (INIT/
  APPEND/FINALIZE/STATUS)

Groq (Publicacao Inteligente):

- `https://api.groq.com/openai/v1/chat/completions` (schema compativel com
  OpenAI, mas nunca chama a OpenAI em si).
- Configuracao: `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_TIMEOUT_SECONDS`,
  `AI_CONTENT_VARIATION_PROMPT_VERSION`,
  `INTELLIGENT_PUBLICATION_CACHE_ENABLED`,
  `INTELLIGENT_PUBLICATION_CACHE_TTL_SECONDS`.
- Sem `GROQ_API_KEY` valida, a aplicacao recusa subir (validacao no startup).

Configuracao geral relevante:

- `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_CALLBACK_URL`, `X_OAUTH_SCOPES`
  (inclui `media.write`), `FRONTEND_URL`, `BACKEND_URL`.
- `JITTER_DEFAULT_MIN_SECONDS`, `JITTER_DEFAULT_MAX_SECONDS`,
  `JITTER_MAX_ALLOWED_SECONDS` (valores iniciais -- depois o admin controla
  via painel, sem mudar `.env`).

## APIs atuais

Health:

- `GET /api/v1/health`
- `GET /api/v1/health/db`

Auth:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password` (primeiro acesso obrigatorio -- ver docs/ROADMAP_PRIMEIRO_ACESSO.md)

Perfil:

- `GET /api/v1/me/subscription`

OAuth X:

- `GET /api/v1/oauth/x/login`
- `GET /api/v1/oauth/x/callback`

Contas do X:

- `GET /api/v1/twitter-accounts`
- `DELETE /api/v1/twitter-accounts/{account_id}`

Posts:

- `POST /api/v1/posts` (aceita `media_ids` e `rendered_texts` opcionais)
- `GET /api/v1/posts`
- `GET /api/v1/posts/{post_id}`
- `POST /api/v1/posts/{post_id}/publish`
- `POST /api/v1/posts/{post_id}/schedule`
- `GET /api/v1/posts/{post_id}/schedule`
- `DELETE /api/v1/posts/{post_id}/schedule`
- `DELETE /api/v1/posts/{post_id}`

Midia (ver docs/ROADMAP_MEDIA.md):

- `POST /api/v1/media/upload`
- `GET /api/v1/media/{media_id}/file`
- `DELETE /api/v1/media/{media_id}`

Publicacao Inteligente (ver docs/ROADMAP_PUBLICACAO_INTELIGENTE.md):

- `POST /api/v1/intelligent-publication/preview`

Admin:

- Usuarios, planos, assinaturas e posts extras sob `/api/v1/admin`.
- `GET /api/v1/admin/posts`, `GET /api/v1/admin/stats`,
  `GET /api/v1/admin/audit-logs`.
- `GET`/`PATCH /api/v1/admin/jitter-settings` (ver docs/ROADMAP_JITTER.md).

## Decisoes que nao devem ser quebradas

- `Post.text` e o texto original do usuario, nunca sobrescrito.
- `PostAccount` representa o fan-out por conta; `rendered_text` e o texto
  final daquela conta.
- Publicacao externa so acontece apos validacoes comerciais completas.
- `PostAccountStatus.PUBLISHED` e terminal para retries de publicacao.
- Tokens OAuth devem permanecer criptografados em repouso (Fernet).
- Rotas nao devem conter regra de negocio.
- A criacao administrativa de usuario exige plano e expiracao de assinatura.
- Nao existe plano/trial implicito no fluxo administrativo atual.
- Toda conta nova nasce com `must_change_password=True` (ver docs/ROADMAP_PRIMEIRO_ACESSO.md).
- Jitter nunca se aplica antes da primeira conta nem com uma unica conta.
- Publicacao Inteligente com 5+ contas nunca cai em fallback de texto igual;
  Groq nunca e substituida por OpenAI.
- Midia e identica em todas as contas de destino; so o texto varia por conta.

## Qualidade e riscos atuais

- Suite `pytest` fina (4 arquivos, cobertura de wiring de rotas), sem teste
  automatizado para `publish_post`, `AIContentVariationService`,
  `JitterService`, scheduler ou funcoes puras de `app.domain`. Validacao de
  cada feature e feita manualmente (curl/scripts descartaveis), documentada
  em `docs/ROADMAP_*.md`.
- Schemas de `Post`/`ScheduledPost` ainda definidos dentro da rota
  (`app/routes/post.py`), nao em `app.schemas` (features mais novas ja usam
  `app.schemas`).
- `app.domain.enums` duplica `UserRole`/`SubscriptionStatus` de
  `app.models.enums` (sincronizacao manual, nao automatica).
- `AuditAction.SUBSCRIPTION_CREATED`/`TWITTER_ACCOUNT_CONNECTED`/
  `TWITTER_ACCOUNT_DISCONNECTED`/`OTHER` existem no enum mas nunca sao
  de fato registrados.
- `app.domain.publication_cost` (custo por tipo de conteudo) nao esta
  conectado ao fluxo real -- todo post consome 1 credito por conta.
- Falha pre-existente e nao relacionada em `pytest`:
  `test_get_subscription_returns_subscription_for_admin`.

Lista completa e detalhada de decisoes, convencoes e dividas tecnicas:
`claude.md`.
