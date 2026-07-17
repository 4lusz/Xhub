# XHub

SaaS para gerenciar múltiplas contas do X (Twitter) por usuário:
conectar contas via OAuth2/PKCE, escrever um post uma única vez e
publicá-lo simultaneamente em uma ou mais contas conectadas, com
controle de acesso por planos e assinaturas administrados por um
administrador da plataforma.

> **Status:** backend e frontend funcionais, com autenticação (JWT +
> refresh token), primeiro acesso obrigatório, gerenciamento
> administrativo completo (usuários, planos, assinaturas, auditoria),
> conexão de múltiplas contas do X via OAuth2/PKCE, upload e edição
> client-side de mídia (imagem/gif/vídeo), criação e publicação de
> posts (com idempotência, consumo de saldo do plano e Jitter entre
> contas), agendamento de posts, e Publicação Inteligente (geração de
> variações de texto via Groq). Não há autocadastro — toda conta é
> criada por um administrador (ver `POST /api/v1/admin/users`).

## Sumário

- [Visão geral](#visão-geral)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Autenticação e autorização](#autenticação-e-autorização)
- [Primeiro acesso obrigatório](#primeiro-acesso-obrigatório)
- [Painel administrativo](#painel-administrativo)
- [Planos e assinaturas](#planos-e-assinaturas)
- [OAuth com o X e múltiplas contas](#oauth-com-o-x-e-múltiplas-contas)
- [Publicação de posts](#publicação-de-posts)
- [Upload e edição de mídia](#upload-e-edição-de-mídia)
- [Publicação Inteligente (Groq)](#publicação-inteligente-groq)
- [Agendamento (scheduler)](#agendamento-scheduler)
- [Jitter](#jitter)
- [Auditoria](#auditoria)
- [Banco de dados](#banco-de-dados)
- [Como rodar (Docker)](#como-rodar-docker)
- [Desenvolvimento sem Docker](#desenvolvimento-sem-docker-opcional)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Observabilidade](#observabilidade)
- [Testes](#testes)
- [Documentação complementar](#documentação-complementar)

## Visão geral

Um usuário cliente conecta uma ou mais contas do X à sua conta XHub,
escreve um post e escolhe para quais contas publicar. O XHub cuida de:
validar se o plano permite aquela publicação (saldo de posts, limite de
contas), variar o texto entre contas quando fizer sentido (Publicação
Inteligente), espaçar as publicações no tempo para parecer uma
atividade humana (Jitter), publicar de fato na API oficial do X, e
manter cada conta com seu próprio status de sucesso/falha —
imediatamente ou agendado para o futuro. Um administrador da
plataforma gerencia usuários, planos, assinaturas e acompanha tudo via
auditoria, sem nunca ver o conteúdo dos posts dos clientes.

## Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL
16, Pydantic v2, JWT, OAuth2/PKCE, APScheduler, Groq (LLM),
`cryptography` (Fernet), bcrypt.

**Frontend:** React 19, TypeScript, Vite, TailwindCSS, shadcn/ui
(Radix UI), React Router, TanStack Query, Axios, Zustand, React Hook
Form + Zod, ffmpeg.wasm, react-easy-crop.

## Arquitetura

Backend em camadas estritas:

```text
HTTP request
-> app/routes      (entrada HTTP, autorização, transação, response model)
-> app/services     (regra de negócio e orquestração)
-> app/repositories  (queries SQLAlchemy)
-> app/models        (ORM)
-> app/domain        (regras puras, sem I/O, chamadas pelos services)
```

Sem fila/broker externo: agendamento roda como worker in-process
(APScheduler) e a Publicação Inteligente usa cache em memória — não há
Redis/RabbitMQ/Celery no projeto.

## Estrutura de pastas

```text
xhub/
├── docker-compose.yml
├── docs/                        # especificação + estado implementado por feature
│   ├── ROADMAP_MEDIA.md
│   ├── ROADMAP_PRIMEIRO_ACESSO.md
│   ├── ROADMAP_PUBLICACAO_INTELIGENTE.md
│   └── ROADMAP_JITTER.md
├── claude.md                    # contexto técnico completo para IA
├── backend/
│   ├── alembic/                  # migrations
│   └── app/
│       ├── config/               # settings (pydantic-settings)
│       ├── database/             # engine, session, base declarativa
│       ├── models/               # User, TwitterAccount, Plan, Subscription, Post,
│       │                         #   PostAccount, PostMedia, ScheduledPost, OAuthSession,
│       │                         #   AuditLog, JitterSettings, RefreshToken
│       ├── domain/                # regras puras de negócio (policies, media_rules, jitter, ...)
│       ├── repositories/          # camada de acesso a dados
│       ├── services/              # regras de negócio e orquestração
│       ├── schemas/                # Pydantic request/response
│       ├── routes/                # health, auth, me, oauth, twitter_account, admin,
│       │                          #   post, media, intelligent_publication
│       ├── oauth/                 # PKCE + integração OAuth2 do X
│       ├── integrations/          # cliente da Groq
│       ├── middleware/            # rate limit, request-id de correlação
│       ├── core/                  # exceções, criptografia, storage de mídia, logging
│       ├── scheduler.py           # worker in-process de agendamento de posts
│       ├── auth/                  # JWT, hashing, refresh token, dependencies de papel
│       ├── scripts/               # scripts operacionais (create_admin.py)
│       └── main.py                # entrypoint da API
└── frontend/
    └── src/
        ├── routes/                # ProtectedRoute, AdminRoute, ClientOnlyRoute
        ├── layouts/                # AuthLayout, DashboardLayout
        ├── pages/                  # uma página por rota
        ├── components/             # admin/, dashboard/, posts/, intelligent-publication/,
        │                          #   accounts/, layout/, common/, ui/ (shadcn)
        ├── hooks/                  # TanStack Query por domínio
        ├── services/                # chamadas axios por domínio
        ├── stores/                  # Zustand (sessão/autenticação)
        ├── types/                   # tipos TS compartilhados
        └── lib/                     # formatação, crop de imagem, regras de mídia
```

## Autenticação e autorização

- Login (`POST /api/v1/auth/login`) emite um par `access_token` (JWT,
  30 min) + `refresh_token` (opaco, hash SHA-256 persistido, 7 dias,
  com **rotação a cada uso** via `POST /api/v1/auth/refresh`).
- `POST /api/v1/auth/logout` revoga um refresh token específico.
- Papéis: `client` e `admin`. Rotas administrativas exigem
  `get_current_admin`; rotas de cliente, `get_current_client`.
- Contas admin **não recebem assinatura** por design — o frontend
  redireciona automaticamente cada papel para sua área (cliente → `/`,
  admin → `/admin`), inclusive bloqueando o acesso cruzado por URL
  direta.
- Tokens OAuth do X ficam cifrados em repouso (Fernet).

## Primeiro acesso obrigatório

Toda conta nasce com uma senha temporária e `must_change_password=true`.
Nenhuma rota protegida (cliente ou admin) funciona além de
`POST /api/v1/auth/change-password` enquanto essa flag estiver ativa —
o backend responde **HTTP 428** e o frontend redireciona para uma tela
dedicada de troca de senha. Completar a troca (ou uma redefinição
administrativa) revoga todas as sessões antigas do usuário. Detalhe
completo em [`docs/ROADMAP_PRIMEIRO_ACESSO.md`](docs/ROADMAP_PRIMEIRO_ACESSO.md).

## Painel administrativo

Área `/admin` (frontend) / `/api/v1/admin` (backend), somente para
`role=admin`:

- **Usuários** — criar (com plano e validade de assinatura explícitos),
  bloquear/desbloquear, trocar papel, redefinir senha (gera senha
  temporária revelada uma única vez).
- **Planos** — editar preço/limites de um plano existente, resincronizar
  o catálogo oficial (`app/domain/plans.py`) com o banco.
- **Assinaturas** — renovar, bloquear, expirar, adicionar/remover posts
  extras (por usuário, via diálogo em "Usuários").
- **Publicações** — visão somente leitura entre todos os usuários,
  filtrável por status; nunca expõe o texto do post, apenas metadados e
  motivo de falha por conta.
- **Auditoria** — log append-only de toda ação administrativa,
  paginado.
- **Jitter** — configura o intervalo mínimo/máximo (segundos) do atraso
  aplicado entre publicações em múltiplas contas (ver seção
  [Jitter](#jitter)).
- **Painel** — estatísticas agregadas (usuários, assinaturas por
  status, posts publicados).

## Planos e assinaturas

- Usuário precisa de assinatura `ACTIVE` para publicar ou conectar
  novas contas; validação com lock (`FOR UPDATE`) antes de qualquer
  efeito externo.
- Saldo = `plan.max_posts_month + subscription.extra_posts - subscription.used_posts`;
  precisa cobrir todas as contas ainda pendentes na chamada de
  publicação.
- Consumo de saldo ocorre por conta publicada com sucesso; contas já
  publicadas nunca são reprocessadas em um retry.
- Custo por conta publicada: **15 créditos** se o texto do post contiver
  um link, **1 crédito** para qualquer outro post (texto simples ou com
  mídia anexada) — mídia nunca altera o custo, só a presença de link no
  texto. Validado (saldo suficiente) antes de qualquer chamada à API do
  X. Ver [`docs/ROADMAP_CUSTO_LINK.md`](docs/ROADMAP_CUSTO_LINK.md).
- Limite de contas conectadas vem do plano vigente da assinatura.
- Catálogo oficial de planos é sincronizado automaticamente no startup
  da aplicação — nenhuma inserção manual é necessária.

## OAuth com o X e múltiplas contas

Fluxo OAuth2 Authorization Code + PKCE completo:

1. `GET /api/v1/oauth/x/login` (autenticado) valida a quota de contas
   antes de iniciar, gera `state`/`code_verifier`/`code_challenge`,
   persiste uma sessão OAuth de uso único no Postgres (10 min de TTL —
   seguro mesmo com múltiplos processos de backend).
2. `GET /api/v1/oauth/x/callback` troca o código por tokens, busca o
   perfil autenticado (com foto), e conecta/atualiza a conta.
3. Usuário pode conectar quantas contas o plano permitir e desconectar
   qualquer uma a qualquer momento.

## Publicação de posts

Fluxo de `POST /api/v1/posts/{post_id}/publish` (idêntico ao usado pelo
scheduler):

1. Remove da tentativa contas já publicadas com sucesso (idempotência).
2. Valida assinatura ativa e saldo suficiente para todas as contas
   pendentes.
3. Para cada conta pendente/falha, na ordem: aplica o atraso do Jitter
   (exceto na primeira conta da chamada), renova o token do X se
   necessário, envia a mídia anexada (se houver) especificamente para
   aquela conta, publica o tweet com o texto renderizado da Publicação
   Inteligente (ou o original), e marca a conta como publicada ou
   falha.
4. Atualiza o status agregado do post.

Também é possível criar um post como rascunho, agendar sua publicação,
ou excluí-lo (o que também remove qualquer mídia anexada do disco).

## Upload e edição de mídia

- Upload (`POST /api/v1/media/upload`, multipart) antes mesmo de o post
  existir — imagem (até 5MB), gif (até 15MB) ou vídeo (até 512MB); até
  4 imagens juntas, ou um único vídeo/gif sozinho.
- A mesma mídia é publicada identicamente em todas as contas de
  destino — apenas o texto varia entre contas.
- **Edição inteiramente client-side**, sem processamento novo no
  backend: crop/zoom/rotação de imagem (canvas + `react-easy-crop`) e
  corte real de vídeo (`ffmpeg.wasm`, remux sem recodificar). O core do
  ffmpeg é self-hosted, nunca servido por um CDN de terceiros.
- Preview em tela cheia (lightbox) com zoom/pan em imagem e player
  nativo para vídeo.

Detalhe completo em [`docs/ROADMAP_MEDIA.md`](docs/ROADMAP_MEDIA.md).

## Publicação Inteligente (Groq)

Gera variações naturais de texto entre contas para reduzir o padrão de
conteúdo repetido — nunca usa OpenAI, exclusivamente Groq.

| Contas selecionadas | Comportamento |
|---|---|
| 1 | Publica o texto original; Groq nunca é chamada. |
| 2 a 4 | Variação **opcional** (ativada por padrão no frontend, com aviso). Se a Groq falhar, cai para o texto original sem bloquear a publicação. |
| 5 ou mais | Variação **obrigatória**. Se a Groq estiver indisponível ou não gerar variações válidas, a publicação é interrompida antes de qualquer chamada ao X — o usuário pode tentar de novo, salvar como rascunho ou reagendar. |

O texto original do usuário (`Post.text`) nunca é sobrescrito; cada
conta guarda seu texto final em `PostAccount.rendered_text`. Toda
variação gerada é validada para preservar exatamente URLs, hashtags,
@menções, emojis e CTA — qualquer variação que altere um desses
elementos é descartada. Um modal de pré-visualização permite editar
manualmente cada versão antes de confirmar a publicação.

Detalhe completo (prompt, cache, tratamento de falhas) em
[`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`](docs/ROADMAP_PUBLICACAO_INTELIGENTE.md).

## Agendamento (scheduler)

Worker in-process (APScheduler), sem infraestrutura adicional de fila:

- `POST /api/v1/posts/{post_id}/schedule` agenda um post para o futuro;
  `DELETE .../schedule` cancela um agendamento ainda não processado.
- A cada `SCHEDULER_INTERVAL_SECONDS` (30s por padrão), o worker
  reivindica agendamentos vencidos com `SELECT ... FOR UPDATE SKIP
  LOCKED` (seguro com múltiplas réplicas do backend) e publica cada um
  usando exatamente o mesmo fluxo da publicação manual.

## Jitter

Publicar em várias contas do mesmo post no mesmo instante é um padrão
facilmente identificável como automação. O Jitter insere um atraso
aleatório **entre** uma conta e a próxima (nunca antes da primeira, e
nunca quando há apenas uma conta), com um valor sorteado
independentemente a cada publicação dentro de um intervalo
mínimo/máximo configurável pelo administrador (`GET`/`PATCH
/api/v1/admin/jitter-settings`), sem precisar reiniciar a aplicação
para a mudança valer. Nunca compromete idempotência, retries, auditoria
ou o funcionamento do scheduler — só adiciona tempo proporcional entre
contas de uma mesma chamada de publicação.

Detalhe completo em [`docs/ROADMAP_JITTER.md`](docs/ROADMAP_JITTER.md).

## Auditoria

Toda ação administrativa relevante (criar/bloquear/desbloquear usuário,
trocar papel, redefinir senha, renovar/bloquear/expirar assinatura,
adicionar/remover posts extras, sincronizar/editar plano, editar
configuração do Jitter) é registrada em um log append-only
(`AuditLog`), consultável via `GET /api/v1/admin/audit-logs`. O log
nunca inclui senhas nem conteúdo de posts.

## Banco de dados

PostgreSQL + SQLAlchemy 2.0 + Alembic. IDs são UUID. Toda mudança de
schema exige uma migration. Tabelas principais: `users`,
`twitter_accounts`, `plans`, `subscriptions`, `posts`, `post_accounts`,
`post_media`, `scheduled_posts`, `oauth_sessions`, `audit_logs`,
`jitter_settings`, `refresh_tokens`.

## Como rodar (Docker)

### 1. Configurar variáveis de ambiente

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Os valores padrão já funcionam para desenvolvimento local (nenhuma
edição é obrigatória nesta etapa — exceto se você for testar OAuth do
X ou a Publicação Inteligente de verdade, ver
[Variáveis de ambiente](#variáveis-de-ambiente)).

### 2. Subir o ambiente

```bash
docker compose up --build
```

| Serviço  | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend  | http://localhost:8000 |
| Docs API | http://localhost:8000/docs |
| Postgres | localhost:5432 (usuário/senha: xhub) |

### 3. Validar o ambiente

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
```

### 4. Aplicar as migrations

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

O catálogo de planos é sincronizado automaticamente no startup — não é
necessária nenhuma inserção manual no banco.

### 5. Criar o primeiro administrador

Não existe autocadastro no XHub — toda conta é criada por um
administrador. Para o primeiro (quando ainda não existe nenhum
usuário):

```bash
docker compose exec backend python -m app.scripts.create_admin
```

A partir daí, use esse administrador para autenticar em
`POST /api/v1/auth/login` (a senha digitada aqui também é temporária —
o primeiro acesso obrigatório troca já se aplica) e criar as demais
contas via painel administrativo ou `POST /api/v1/admin/users`.

## Desenvolvimento sem Docker (opcional)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Nesse caso, suba um PostgreSQL local ou aponte `DATABASE_URL` para um
banco existente.

## Variáveis de ambiente

Principais grupos em `backend/.env` (ver `backend/.env.example` para a
lista completa e comentada):

- **Geral**: `ENVIRONMENT`, `DEBUG`, `DATABASE_URL`.
- **JWT**: `JWT_SECRET_KEY` (mín. 32 chars fora de `development`),
  `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`,
  `JWT_REFRESH_TOKEN_EXPIRE_DAYS`.
- **Criptografia**: `TOKEN_ENCRYPTION_KEY` (Fernet, cifra tokens OAuth
  em repouso).
- **OAuth do X**: `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_CALLBACK_URL`,
  `X_OAUTH_SCOPES` (inclui `media.write` — contas conectadas antes
  dessa mudança precisam reconectar para publicar mídia),
  `FRONTEND_URL`, `BACKEND_URL`.
- **CORS / rate limit**: `CORS_ORIGINS`, `AUTH_RATE_LIMIT_*`,
  `TRUST_PROXY_HEADERS`.
- **Scheduler**: `SCHEDULER_ENABLED`, `SCHEDULER_INTERVAL_SECONDS`,
  `SCHEDULER_BATCH_SIZE`.
- **Publicação Inteligente / Groq**: `GROQ_API_KEY`, `GROQ_MODEL`,
  `GROQ_TIMEOUT_SECONDS`, `AI_CONTENT_VARIATION_PROMPT_VERSION`,
  `INTELLIGENT_PUBLICATION_CACHE_ENABLED`,
  `INTELLIGENT_PUBLICATION_CACHE_TTL_SECONDS`,
  `AI_CONTENT_VARIATION_MAX_BATCH_SIZE` (posts com mais contas do que
  este valor têm a geração de variações dividida automaticamente em
  várias chamadas menores à Groq — ver
  `docs/ANALISE_ESCALABILIDADE.md`). Sem `GROQ_API_KEY` configurada, a
  aplicação não sobe (validação na inicialização).
- **Mídia**: `MEDIA_STORAGE_DIR`, `X_MEDIA_UPLOAD_CHUNK_SIZE_BYTES`,
  `X_MEDIA_UPLOAD_TIMEOUT_SECONDS`, `X_MEDIA_STATUS_MAX_WAIT_SECONDS`.
- **Jitter**: `JITTER_DEFAULT_MIN_SECONDS`, `JITTER_DEFAULT_MAX_SECONDS`
  (valores iniciais — depois disso o admin controla via painel, sem
  precisar mudar `.env`), `JITTER_MAX_ALLOWED_SECONDS` (teto de
  segurança).

Frontend: `VITE_API_URL` (`frontend/.env`).

## Observabilidade

Logging estruturado (JSON, um objeto por linha) em toda a aplicação
backend, incluindo `request_id` de correlação por requisição (header
`X-Request-ID`, gerado automaticamente se ausente) e um handler global
de exceções que garante que nenhum erro não tratado desapareça sem
deixar rastro.

## Testes

`backend/tests/` contém uma suíte `pytest` fina (testes de wiring/
serialização de rotas específicas, sem banco/HTTP reais — usa
dependency overrides com dublês). Cada funcionalidade nova é validada
manualmente contra a API real (curl e/ou scripts descartáveis) durante
o desenvolvimento; os resultados dessa validação ficam documentados em
`docs/ROADMAP_*.md`. Não há suíte de testes E2E de frontend automatizada.

```bash
docker compose exec backend pytest
```

## Documentação complementar

- [`claude.md`](claude.md) — contexto técnico completo para IA
  (arquitetura, convenções, decisões, regras de negócio, dívidas
  técnicas conhecidas).
- [`docs/ROADMAP_MEDIA.md`](docs/ROADMAP_MEDIA.md) — mídia (upload,
  edição client-side, contas com foto de perfil).
- [`docs/ROADMAP_PRIMEIRO_ACESSO.md`](docs/ROADMAP_PRIMEIRO_ACESSO.md)
  — primeiro acesso obrigatório e redefinição administrativa de senha.
- [`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`](docs/ROADMAP_PUBLICACAO_INTELIGENTE.md)
  — Publicação Inteligente e integração com a Groq.
- [`docs/ROADMAP_JITTER.md`](docs/ROADMAP_JITTER.md) — atraso natural
  entre publicações em múltiplas contas.
- [`docs/ANALISE_ESCALABILIDADE.md`](docs/ANALISE_ESCALABILIDADE.md) —
  análise arquitetural de escalabilidade para clientes com muitas
  contas conectadas (10 a 100).
- [`docs/AUDITORIA_FUNCIONAL.md`](docs/AUDITORIA_FUNCIONAL.md) —
  auditoria funcional completa (problemas encontrados, correções,
  validações executadas).
- [`docs/ROADMAP_CUSTO_LINK.md`](docs/ROADMAP_CUSTO_LINK.md) — custo
  diferenciado por conta para posts com link.
- [`docs/AUDITORIA_SEGURANCA.md`](docs/AUDITORIA_SEGURANCA.md) —
  auditoria completa de segurança (vulnerabilidades encontradas,
  correções, dependências com CVE avaliadas, cobertura OWASP Top 10).
- `backend/CHANGELOG.md` / `frontend/CHANGELOG.md` — histórico
  detalhado de mudanças por camada.
