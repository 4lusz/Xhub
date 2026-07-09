# XHub

SaaS para gerenciamento de multiplas contas do X (Twitter) via API oficial
(OAuth 2.0), com publicacao simultanea e agendamento de posts.

> **Status:** backend funcional com autenticacao (login por JWT),
> gerenciamento administrativo de usuarios/planos/assinaturas, conexao
> de contas do X via OAuth2/PKCE, criacao e publicacao de posts (com
> idempotencia e consumo de saldo do plano) e agendamento de posts
> (worker in-process que publica automaticamente no horario definido).
> Nao ha auto cadastro de usuarios: toda conta e criada por um
> administrador, que escolhe o plano explicitamente (ver
> `POST /api/v1/admin/users`).

## Stack

**Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL,
Pydantic v2, JWT, OAuth2, APScheduler.

**Frontend:** React, TypeScript, Vite, TailwindCSS, React Router,
TanStack Query, Axios.

## Estrutura de pastas

```
xhub/
├── docker-compose.yml
├── backend/
│   ├── alembic/                 # migrations
│   └── app/
│       ├── config/               # settings (pydantic-settings)
│       ├── database/             # engine, session, base declarativa
│       ├── models/                # models SQLAlchemy: User, TwitterAccount,
│       │                          # Plan, Subscription, Post, PostAccount,
│       │                          # ScheduledPost
│       ├── repositories/          # camada de acesso a dados
│       ├── services/              # regras de negocio
│       ├── routes/                # rotas FastAPI: health, auth, oauth,
│       │                          # twitter_account, admin, post
│       ├── oauth/                 # integracao OAuth2 do X
│       ├── middleware/            # rate limit, request-id de correlacao
│       ├── core/                  # excecoes, logging estruturado, bootstrap
│       ├── scheduler.py           # worker in-process de agendamento de posts
│       ├── auth/                  # JWT, hashing, dependencies de auth
│       ├── scripts/                # scripts operacionais (ex.: create_admin.py)
│       └── main.py                # entrypoint da API
└── frontend/
    └── src/
        ├── pages/
        ├── components/
        ├── layouts/
        ├── hooks/
        ├── contexts/
        ├── services/               # axios instance
        └── types/
```


## Como rodar

### 1. Configurar variaveis de ambiente

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Os valores padrao ja funcionam para desenvolvimento local com Docker
Compose (nenhuma edicao e obrigatoria nesta etapa).

### 2. Subir o ambiente

```bash
docker compose up --build
```

Isso vai subir 3 containers:

| Servico  | URL                              |
|----------|-----------------------------------|
| Frontend | http://localhost:5173             |
| Backend  | http://localhost:8000              |
| Docs API | http://localhost:8000/docs         |
| Postgres | localhost:5432 (user/senha: xhub)|

### 3. Validar o ambiente

Abra http://localhost:5173 &mdash; a tela deve mostrar dois indicadores
("API (FastAPI)" e "Banco de dados (PostgreSQL)") ficando verdes.

Ou via curl:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
```

### 4. Aplicar as migrations

Com os containers no ar (`docker compose up`), aplique as migrations
(cria `users`, `twitter_accounts`, `plans`, `subscriptions`,
`posts`, `post_accounts`, `scheduled_posts`, `oauth_sessions`):

```bash
docker compose exec backend alembic upgrade head
```

Para conferir:

```bash
docker compose exec backend alembic current
docker compose exec db psql -U xhub -d xhub -c "\dt"
```

O catalogo oficial de planos (`app/domain/plans.py`) e sincronizado
automaticamente com a tabela `plans` no startup da aplicacao -- nao e
necessaria nenhuma insercao manual no banco. Caso o catalogo ganhe um
novo plano com a aplicacao ja no ar, um administrador pode forcar uma
nova sincronizacao via `POST /api/v1/admin/plans/sync`.

### 5. Criar o primeiro administrador

Nao existe auto cadastro no XHub -- toda conta e criada por um
administrador. Para o primeiro administrador (quando ainda nao existe
nenhum usuario), use o script incluso:

```bash
docker compose exec backend python -m app.scripts.create_admin
```

A partir dai, use esse administrador para autenticar em
`POST /api/v1/auth/login` e criar as demais contas via
`POST /api/v1/admin/users` (escolhendo explicitamente o plano de cada
uma).

Os models usam `id` do tipo UUID (em vez de inteiro sequencial), o que
e o padrao recomendado para SaaS multi-tenant (IDs nao previsiveis). Os
tokens do OAuth2 do X (`access_token`/`refresh_token` em
`TwitterAccount`) sao criptografados em repouso (Fernet) antes de
serem persistidos.

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

## Agendamento de posts

O agendamento roda como um worker in-process (APScheduler), iniciado
junto com a aplicacao (sem infraestrutura adicional como filas/broker):

- `POST /api/v1/posts/{post_id}/schedule` agenda um post existente para
  uma data/hora futura.
- `DELETE /api/v1/posts/{post_id}/schedule` cancela um agendamento
  ainda nao processado.
- A cada `SCHEDULER_INTERVAL_SECONDS` (30s por padrao), o worker
  verifica os agendamentos vencidos e os publica usando o mesmo fluxo
  de `POST /api/v1/posts/{post_id}/publish`. Seguro mesmo com multiplos
  processos/workers do backend rodando ao mesmo tempo (usa
  `SELECT ... FOR UPDATE SKIP LOCKED` no Postgres para evitar
  publicacao duplicada).

## Observabilidade

Logging estruturado (JSON, um objeto por linha) para toda a aplicacao,
incluindo um `request_id` de correlacao por requisicao (header
`X-Request-ID`, gerado automaticamente se o cliente nao enviar um) e um
handler global de excecoes que garante que nenhum erro nao tratado
desapareça sem deixar rastro.

