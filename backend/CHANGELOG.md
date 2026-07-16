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
