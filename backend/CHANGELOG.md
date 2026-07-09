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
