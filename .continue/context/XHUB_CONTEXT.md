# XHub - Contexto permanente para IA de desenvolvimento

Este documento e contexto tecnico permanente para Continue.dev. Ele descreve o
estado observado no codigo do projeto em 2026-07-09.

## Produto

XHub e um SaaS para gerenciar multiplas contas do X (Twitter) por usuario,
publicar posts em uma ou mais contas conectadas via OAuth2 e controlar uso por
planos/assinaturas.

## Estado atual observado

Backend implementado:

- FastAPI com prefixo `/api/v1`.
- Health checks de API e banco.
- Autenticacao por JWT.
- Usuarios com roles `client` e `admin`.
- Criacao administrativa de usuarios com assinatura explicita.
- Planos e assinaturas com limites de contas e posts mensais.
- Posts extras por assinatura.
- Auditoria administrativa.
- OAuth2 do X com PKCE.
- Contas do X conectadas por usuario.
- Criacao, listagem, consulta, exclusao e publicacao de posts.
- Fan-out de publicacao por conta usando `PostAccount`.
- Refresh de access token do X quando expirado.
- Publicacao via API oficial do X em `POST https://api.x.com/2/tweets`.

Frontend implementado:

- Tela inicial de health check.
- Hooks para health da API e do banco.
- Axios configurado em `frontend/src/services/api.ts`.

Inconsistencia documentada:

- O README anterior dizia que ainda nao havia rotas, repositories e services.
  Isso estava desatualizado em relacao ao codigo atual.

## Arquitetura backend

Camadas principais:

- `routes`: entrada HTTP, Depends, autorizacao, commit/rollback, response models.
- `services`: regras de negocio e orquestracao de repositories/clientes externos.
- `repositories`: queries SQLAlchemy e persistencia.
- `models`: SQLAlchemy ORM e relacionamentos.
- `domain`: regras puras, policies, dataclasses e enums independentes de framework.
- `auth`: JWT, password hashing e dependencies de usuario atual.
- `oauth`: OAuth2/PKCE, cliente HTTP do X e service de conexao de contas.
- `config`: settings centralizados via pydantic-settings.
- `core`: excecoes, criptografia, constantes e seguranca.

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

## Banco de dados

Persistencia usa PostgreSQL, SQLAlchemy 2.0 e Alembic.

Models principais:

- `User`: usuario da plataforma.
- `TwitterAccount`: conta do X conectada via OAuth2.
- `Plan`: limites comerciais.
- `Subscription`: assinatura do usuario, uso de posts e posts extras.
- `Post`: texto original criado pelo usuario e status agregado.
- `PostAccount`: uma linha por par `(Post, TwitterAccount)`.
- `ScheduledPost`: agendamento associado a um post.
- `OAuthSession`: estado temporario do fluxo OAuth/PKCE.
- `AuditLog`: trilha de auditoria administrativa.

Padroes:

- IDs sao UUID.
- `TimestampMixin` fornece `created_at` e `updated_at`.
- Mudancas de schema exigem migration Alembic.
- Relacionamentos usam cascade quando o agregado deve apagar dependentes.

## Autenticacao e autorizacao

- Login gera JWT.
- `OAuth2PasswordBearer` espera token em `/api/v1/auth/login`.
- `get_current_user` valida token, carrega usuario e bloqueia usuario bloqueado.
- `get_current_admin` exige role admin.
- `get_current_client` exige role client.
- Rotas administrativas dependem de `get_current_admin`.

## Assinaturas e limites

Regras atuais:

- Usuario precisa de assinatura ativa para publicar.
- Assinatura e validada com lock `FOR UPDATE` antes de publicacao.
- O saldo precisa cobrir todas as contas que ainda serao publicadas na chamada.
- O consumo (`used_posts`) ocorre por conta publicada com sucesso.
- Contas ja publicadas com sucesso nao sao reprocessadas.
- Limite de contas conectadas vem do plano da assinatura.

## Publicacao atual

Fluxo atual de `POST /posts/{post_id}/publish`:

1. Rota carrega o post e valida posse pelo usuario autenticado.
2. `PostService.publish_post` busca `PostAccount` do post.
3. Remove da tentativa contas ja `PUBLISHED`.
4. Valida assinatura ativa e saldo antes de qualquer chamada externa.
5. Para cada conta pendente/falha, obtem token valido.
6. Chama `XOAuthClient.publish_post` usando `Post.text`.
7. Marca cada `PostAccount` como `PUBLISHED` ou `FAILED`.
8. Atualiza o `Post.status` agregado para `PUBLISHED` ou `FAILED`.

Limitacao atual importante:

- `PostAccount` ainda nao possui `rendered_text`.
- Todas as contas recebem exatamente `Post.text`.
- A Publicacao Inteligente deve preservar `Post.text` como texto original e usar
  `PostAccount.rendered_text` como texto final por conta.

## Integracoes externas

X API:

- Autorizacao: `https://x.com/i/oauth2/authorize`
- Token: `https://api.x.com/2/oauth2/token`
- Usuario autenticado: `https://api.x.com/2/users/me`
- Publicacao: `https://api.x.com/2/tweets`

Configuracao:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_CALLBACK_URL`
- `X_OAUTH_SCOPES`
- `FRONTEND_URL`
- `BACKEND_URL`

Groq:

- Ainda nao existe integracao implementada.
- A especificacao oficial esta em `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`.

## APIs atuais

Health:

- `GET /api/v1/health`
- `GET /api/v1/health/db`

Auth:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

OAuth X:

- `GET /api/v1/oauth/x/login`
- `GET /api/v1/oauth/x/callback`

Contas do X:

- `GET /api/v1/twitter-accounts`
- `DELETE /api/v1/twitter-accounts/{account_id}`

Posts:

- `POST /api/v1/posts`
- `GET /api/v1/posts`
- `GET /api/v1/posts/{post_id}`
- `POST /api/v1/posts/{post_id}/publish`
- `DELETE /api/v1/posts/{post_id}`

Admin:

- Usuarios, planos, assinaturas e posts extras sob `/api/v1/admin`.

## Decisoes que nao devem ser quebradas

- `Post.text` e o texto original do usuario.
- `PostAccount` representa o fan-out por conta.
- Publicacao externa so acontece apos validacoes comerciais completas.
- `PostAccountStatus.PUBLISHED` e terminal para retries de publicacao.
- Tokens OAuth devem permanecer criptografados em repouso.
- Rotas nao devem conter regras de negocio.
- A criacao administrativa de usuario exige plano e expiracao de assinatura.
- Nao existe plano/trial implicito no fluxo administrativo atual.

## Qualidade e riscos atuais

- O frontend esta atras do backend em funcionalidades.
- Schemas de posts estao definidos dentro da rota, nao em `app.schemas`.
- `PostAccount.rendered_text` ainda nao existe e exigira migration.
- Nao foi observado suite de testes no repositorio.
- README estava desatualizado e foi corrigido para refletir o codigo atual.
