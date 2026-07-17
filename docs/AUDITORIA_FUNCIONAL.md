# Auditoria funcional completa — XHub

Data: 2026-07-17. Escopo: validação de ponta a ponta de todo o
funcionamento do sistema antes da auditoria de segurança final.
Nenhuma funcionalidade nova foi implementada; apenas problemas reais
identificados durante a auditoria foram corrigidos, seguindo a
arquitetura já existente.

## Metodologia

1. Leitura completa da arquitetura (`claude.md`, `README.md`, todos os
   `docs/ROADMAP_*.md`, `docs/ANALISE_ESCALABILIDADE.md`) e do código de
   cada camada (routes, services, repositories, domain, models, schemas,
   frontend) antes de qualquer validação — código tratado como fonte da
   verdade em qualquer divergência com a documentação.
2. Validação **ao vivo** contra a stack real (Docker Compose: Postgres +
   backend + frontend), via `curl` autenticado usando contas de teste já
   existentes (`admin@xhub.test`, `cliente2@xhub.test`) e contas
   descartáveis criadas e removidas ao final de cada verificação.
3. Um script Python descartável (`backend/tests/_manual_functional_audit.py`,
   criado, executado e apagado ao final — mesmo padrão já usado neste
   projeto para Media/Jitter/Publicação Inteligente) validou 40 asserções
   de regra de negócio de ponta a ponta usando dublês de `XOAuthClient` e
   `GroqClient` (nunca a API real do X/Groq), incluindo publicação com 1,
   3 e 4 contas, Jitter, retries, saldo, limite de contas, scheduler e
   Publicação Inteligente nos três regimes (1 / 2-4 / 5+ contas).
4. Frontend: validado via `tsc --noEmit` + `npm run build` limpos, e
   revisão completa de código de toda página/componente (estados de
   loading, vazio e erro) — sem ferramenta de automação de navegador
   disponível neste ambiente (mesma limitação já registrada nas
   validações anteriores deste projeto).
5. Nenhuma validação por tentativa e erro: todo problema encontrado foi
   primeiro entendido lendo o código (causa raiz), só então corrigido.

## Resumo executivo

| Módulo | Resultado |
|---|---|
| Autenticação (login/logout/JWT/refresh/primeiro acesso/bloqueio) | **2 problemas reais corrigidos** |
| Administração (usuários/planos/assinaturas/auditoria/Jitter) | Aprovado sem alterações |
| Área do cliente (dashboard/perfil/configurações/contas) | **1 problema real corrigido** (texto enganoso) |
| Publicações (criação/publicação/agendamento/histórico/cancelamento) | **1 problema real corrigido** (exclusão de post publicado) |
| Publicação Inteligente (1 / 2-4 / 5+ contas, invariantes) | Aprovado sem alterações |
| Upload de mídia (imagem/vídeo/editor/crop/trim) | Aprovado sem alterações |
| Regras de consumo e limites | Aprovado sem alterações (1 item documentado como não implementado, ver seção própria) |
| Scheduler (agendamento/Jitter/retries) | Aprovado sem alterações |
| Banco de dados (entidades/migrations/integridade) | Aprovado sem alterações |
| Backend (services/repositories/routes/schemas/exceções/logs) | **1 gap de mapeamento HTTP corrigido** |
| Frontend (navegação/loading/vazio/erro/consistência) | Aprovado, com **1 correção de precisão de regra** |
| Escalabilidade (10/20/50/100 contas) | Reconfirmado — nenhum gargalo novo além dos já documentados em `docs/ANALISE_ESCALABILIDADE.md` |
| Infraestrutura de testes (`pytest`) | **2 problemas reais corrigidos** (reprodutibilidade + teste desatualizado) |

## Problemas encontrados, causa raiz e correção

### 1. Login não bloqueava usuário bloqueado (Autenticação)

**Causa raiz:** `AuthService.authenticate` (usado por `POST /auth/login`)
verificava apenas email/senha, nunca `user.is_blocked` — apesar do
próprio docstring de `app.domain.policies.ensure_user_not_blocked` já
declarar a regra ("usuário não pode logar nem realizar nenhuma ação") e
de `AuthService.rotate_refresh_token` (renovação de sessão) já fazer
essa checagem corretamente. Um usuário bloqueado conseguia completar o
login normalmente e receber um par de tokens válidos, só esbarrando no
bloqueio na primeira chamada subsequente.

**Correção:** adicionada a checagem em `AuthService.authenticate`,
levantando `ForbiddenException("Usuario bloqueado.")` — mesma exceção e
mensagem já usadas em todo o resto da aplicação para este caso,
garantindo tratamento uniforme no frontend independente da rota.

**Validado:** `POST /auth/login` com um usuário bloqueado agora retorna
`403 {"detail":"Usuario bloqueado."}` em vez de `200` com tokens
válidos (testado ao vivo, criando e bloqueando um usuário descartável).

### 2. Mensagem/status inconsistentes ao renovar sessão de usuário bloqueado

**Causa raiz:** `AuthService.rotate_refresh_token` misturava "usuário
não encontrado" e "usuário bloqueado" sob a mesma exceção
(`UnauthorizedException`, HTTP 401, mensagem genérica "Usuario nao
encontrado ou bloqueado."), diferente do padrão usado em qualquer outra
rota protegida (`ForbiddenException`, HTTP 403, "Usuario bloqueado.").

**Correção:** separadas as duas causas — usuário inexistente continua
`UnauthorizedException` (401, "Refresh token invalido."); usuário
bloqueado agora usa `ForbiddenException` (403, "Usuario bloqueado."),
idêntico ao restante do sistema.

**Validado:** `POST /auth/refresh` com o refresh token de um usuário
bloqueado no meio da sessão retorna `403 {"detail":"Usuario
bloqueado."}` (testado ao vivo).

### 3. `routes/auth.py` não mapeava `ForbiddenException` para HTTP 403

**Causa raiz:** consequência direta dos itens 1-2 — o `_raise_http_error`
local de `app/routes/auth.py` nunca precisou de uma branch para
`ForbiddenException` (nenhum service chamado por essa rota o levantava
antes). Sem a correção, as duas exceções acima cairiam no branch
default (400 Bad Request) em vez de 403.

**Correção:** adicionada a branch `ForbiddenException → 403`, mesmo
padrão já usado em `app/routes/post.py`.

**Validado:** junto com os itens 1 e 2 (status HTTP correto confirmado
nas respostas).

### 4. Post publicado podia ser excluído, apagando o histórico real de publicação

**Causa raiz:** `PostService.delete_post` não validava o status das
contas do post antes de excluir. `PostAccount` é a única linha do XHub
que registra que uma publicação realmente aconteceu no X (`x_post_id`);
excluir o `Post` apaga em cascata (`Post.post_accounts`, `cascade="all,
delete-orphan"`) todas as suas `PostAccount`, mesmo as `PUBLISHED`. O
frontend (`PostsPage.tsx`) já escondia o botão "Excluir" quando
`post.status === "published"`, mas essa é a condição do status
*agregado* — um post com falha parcial (`status === "failed"` com,
por exemplo, 2 de 3 contas `published`) não era barrado nem no
frontend nem no backend, permitindo apagar o registro de publicações
que de fato aconteceram no X.

**Correção:**
- Backend (`PostService.delete_post`): recusa a exclusão
  (`ConflictException`, HTTP 409) se qualquer `PostAccount` do post
  estiver `PUBLISHED` — única fonte de verdade real, independente do
  que o frontend mostra ou de chamadas diretas à API.
- Frontend (`PostsPage.tsx`): condição do botão "Excluir" corrigida de
  `post.status !== "published"` para `post.accounts.every(a =>
  a.status !== "published")`, espelhando a regra real.

**Validado:** script descartável — post com falha parcial (2
publicadas, 1 falha) tem a exclusão recusada com 409; post totalmente
sem contas publicadas continua podendo ser excluído normalmente
(regressão verificada).

### 5. Texto do diálogo de desconexão de conta do X induzia a erro

**Causa raiz:** `AccountsPage.tsx` avisava "Posts já publicados não são
afetados" ao desconectar uma conta — mas `TwitterAccount.post_accounts`
tem `cascade="all, delete-orphan"`: desconectar (excluir) a conta
apaga em cascata todas as suas `PostAccount`, inclusive as `PUBLISHED`
(perdendo `x_post_id` e o histórico local dessas publicações, mesmo o
tweet continuando publicado no X). A afirmação era factualmente
incorreta.

**Correção:** texto do `ConfirmDialog` corrigido para descrever o
comportamento real: "Os tweets já publicados continuam no X
normalmente, mas o histórico dessa conta no XHub será removido...".
Nenhuma mudança de comportamento — apenas a comunicação passou a
refletir a realidade, para que o usuário decida com informação
correta. (Diferente do item 4: aqui a exclusão em si não foi bloqueada,
porque desconectar uma conta é uma ação legítima e esperada a qualquer
momento — a correção certa é comunicar a consequência, não impedi-la.)

**Validado:** revisão do texto atualizado; `tsc`/`build` limpos.

### 6. `pytest` ausente de `requirements.txt` — suíte não roda em uma imagem construída do zero

**Causa raiz:** `backend/requirements.txt` nunca declarou `pytest`,
apesar de `backend/tests/` conter testes reais e de toda a
documentação do projeto (README, `claude.md`, CHANGELOGs de features
anteriores) instruir `docker compose exec backend pytest` como o
comando padrão de validação. Isso só não havia sido percebido porque o
container de desenvolvimento usado nas sessões anteriores deste
projeto teve o pacote instalado manualmente em algum momento (fora do
Dockerfile) e nunca foi reconstruído do zero — um `docker compose up
--build` limpo (confirmado nesta auditoria, quando os containers
precisaram ser recriados) não tem `pytest` disponível.

**Correção:** adicionado `pytest==8.3.4` a `backend/requirements.txt`.

**Validado:** `docker compose build backend` (reconstrução completa,
sem cache do pacote) seguido de `docker compose exec backend pytest -q`
— suíte roda normalmente a partir de uma imagem 100% nova.

### 7. Teste `test_get_subscription_returns_subscription_for_admin` desatualizado

**Causa raiz:** dublê `FakeSubscriptionService` (dentro do próprio
teste) nunca foi atualizado para acompanhar `SubscriptionService`
(métodos `to_domain_context`/`get_available_posts`, adicionados junto
da funcionalidade de tela "Assinatura" do admin) nem o schema
`SubscriptionResponse` (campos `available_posts`/`used_accounts`/`plan`,
adicionados na mesma etapa) — o teste falhava desde então com
`AttributeError`, documentado (corretamente, na época) como
"pré-existente e não relacionada" em todas as features seguintes.
Agora que o escopo desta auditoria é justamente varrer inconsistências
remanescentes, foi corrigido.

**Correção:** dublê atualizado para implementar a mesma interface do
service real; asserção do corpo de resposta atualizada para o schema
atual completo.

**Validado:** `pytest -q` — **6 passaram, 0 falharam** (primeira vez
neste projeto com a suíte inteiramente verde).

## Validações executadas (lista completa)

**Autenticação:** login válido/inválido; `GET /auth/me` sem token, com
token inválido, com token válido; `GET /admin/users` como cliente (403)
e como admin (200); rotação de refresh token (uso único, reuso
rejeitado); logout revoga o refresh token; primeiro acesso obrigatório
completo (criação → login com senha temporária → 428 em toda rota
protegida → troca de senha com a mesma senha (422) → senha curta (422)
→ troca válida → login normal); bloqueio/desbloqueio de conta com
efeito imediato na sessão; mudança de papel; redefinição administrativa
de senha (revoga sessões, força novo primeiro acesso); login/refresh
com usuário bloqueado (403, correção validada).

**Administração:** listar/editar/sincronizar planos; validação de
preço inválido (422); configurar Jitter (get/patch, validação
min>max); auditoria (listagem, ações e detalhes corretos, nunca
inclui senha); estatísticas agregadas.

**Publicações / Publicação Inteligente / Regras de consumo /
Scheduler** (via script descartável com dublês, 40 asserções): 1 conta
sem Jitter; 4 contas com Jitter (gaps independentes, dentro do
intervalo configurado); falha parcial + retry (idempotência, consumo
de saldo correto, sem republicar conta já publicada); Publicação
Inteligente com 1 conta (Groq nunca chamada), 2-4 contas (ativada e
desativada), 5+ contas (obrigatória, variações distintas, invariantes
preservados); Groq indisponível (fallback silencioso em 2-4 contas,
bloqueio total em 5+); preservação de invariantes (URL com pontuação,
troca de domínio rejeitada, remoção de hashtag/menção rejeitada,
reordenação aceita); saldo insuficiente bloqueia publicação antes de
qualquer chamada ao X; limite de contas do plano bloqueia nova conexão;
scheduler (claim um-a-um, publicação, Jitter, `executed`/`attempts`
corretos); cancelamento de agendamento; exclusão de post não publicado;
exclusão de post com sucesso parcial recusada (409, correção validada).

**Upload de mídia** (via HTTP real): upload de imagem válida (201);
download byte-idêntico ao original; tipo não suportado rejeitado (422);
isolamento entre usuários (outro usuário não acessa a mídia, 404 sem
revelar existência); acesso sem token (401); remoção de mídia não
anexada (204); confirmação de remoção (404 subsequente).

**Publicações via HTTP real (rotas completas):** criação, leitura,
isolamento por dono (403 para outro usuário), agendamento, leitura do
agendamento, cancelamento, exclusão.

**Banco de dados:** cadeia de 18 migrations verificada como linear, sem
ramificações nem migrations órfãs (`down_revision` de cada uma
conferido); `alembic current` confirma HEAD aplicado; constraints
revisadas (`uq_subscriptions_one_active_per_user` — índice parcial
único; `uq_post_twitter_account`; `uq_user_twitter_account`; FKs com
`ondelete` apropriado por relação).

**Backend:** revisão completa de `routes`, `services`, `repositories`,
`domain`, `schemas`, `core/exceptions`, `middleware` (rate limit e
request-id), `main.py` (bootstrap, lifespan, exception handler global).

**Frontend:** revisão completa de todas as páginas e componentes
relevantes (autenticação, guards de rota, admin, cliente, posts, mídia,
Publicação Inteligente) — estados de loading/vazio/erro presentes e
consistentes em todas as telas revisadas; `tsc --noEmit` e `npm run
build` limpos após as correções.

**Escalabilidade:** reconfirmado que as três correções da análise
anterior (`docs/ANALISE_ESCALABILIDADE.md` — scheduler um-a-um, batching
de variações da Groq, reuso de conexão HTTP no `XOAuthClient`)
continuam intactas e em uso (exercitadas pelo próprio script de
auditoria funcional, cenário do scheduler); nenhum gargalo novo
identificado além dos já documentados.

## Itens conhecidos, não alterados nesta auditoria (com justificativa)

- ~~**"Publicação contendo link consome 15 créditos"**: não implementado,
  fora do escopo desta auditoria por exigir funcionalidade nova.~~
  **Atualização (2026-07-17, mesmo dia):** o usuário confirmou
  explicitamente que esta é uma regra de negócio necessária e pediu a
  implementação. Feita em seguida à publicação deste relatório — ver
  [`docs/ROADMAP_CUSTO_LINK.md`](ROADMAP_CUSTO_LINK.md) para a
  especificação completa e a validação executada. Este item não é mais
  uma lacuna: `PostService.publish_post` agora consome 15 créditos por
  conta publicada quando `Post.text` contém um link, e 1 crédito por
  conta em qualquer outro caso.
- **`AuditAction.SUBSCRIPTION_CREATED`/`TWITTER_ACCOUNT_CONNECTED`/`TWITTER_ACCOUNT_DISCONNECTED`/`OTHER`**
  existem no enum mas nunca são de fato registrados (criar assinatura
  via `POST /admin/users`, conectar/desconectar conta do X não geram
  entrada de auditoria hoje). Pré-existente, já documentado, fora do
  escopo de correção desta tarefa (adicionar esses registros de
  auditoria não é uma correção de um problema funcional, é uma
  funcionalidade de auditoria adicional).
- **Sem logout forçado no frontend quando uma conta é bloqueada em
  sessão já ativa**: hoje qualquer 403 (bloqueio de conta, papel
  incorreto, limite de plano, etc.) é tratado apenas como erro comum
  de requisição — não há um redirecionamento dedicado como o que
  existe para 401 (sessão expirada) e 428 (primeiro acesso). Adicionar
  isso exigiria distinguir "bloqueio de conta" de outros 403 (hoje
  todos usam o mesmo código HTTP e mensagens diferentes) — um contrato
  de erro novo, não uma correção contida. Registrado como recomendação
  para decisão futura.
- **Publicação imediata síncrona** (`POST /posts/{id}/publish`) continua
  podendo levar minutos para 100 contas — já analisado e documentado em
  `docs/ANALISE_ESCALABILIDADE.md` como risco residual aceito, não
  alterado por ser uma mudança de arquitetura maior (publicação
  assíncrona), fora do escopo desta auditoria funcional.
- **`GET /twitter-accounts` com teto rígido de 100**: coincide
  exatamente com o maior plano do catálogo (Agência, 100 contas) — não
  é uma falha observável hoje, só um ponto de atenção se o catálogo
  algum dia permitir mais de 100 contas.
- **Mudança de papel admin→cliente sem assinatura**: gera um cliente
  sem plano ativo — degrada graciosamente (mesmo tratamento já usado
  para qualquer usuário sem assinatura), não é um erro/crash. Não
  alterado.

## Conclusão

Todos os módulos do escopo foram auditados. Sete problemas reais foram
encontrados, todos corrigidos na causa raiz seguindo os padrões já
estabelecidos no projeto (mesmas exceções, mesmos mapeamentos HTTP,
mesma separação de camadas), e revalidados com sucesso — nenhuma
funcionalidade nova foi introduzida. O ambiente termina esta auditoria
com `pytest` 100% verde (pela primeira vez), `tsc`/`build` do frontend
limpos, e os três containers saudáveis na versão de migration mais
recente (`f6a7b8c9d0e1`).
