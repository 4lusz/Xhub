# Changelog

## 2026-07-23 - Auditoria de segurança completa pré-commit (JWT + rate limiting)

Pedida explicitamente pelo usuário antes de um commit, seguindo um
checklist de 7 itens (rate limiting, CORS, PII, JWT, enumeração de
usuários, clickjacking/headers, SQLi/IDOR) no backend inteiro. Detalhe
completo em `docs/AUDITORIA_SEGURANCA.md`.

**2 achados reais, corrigidos:**
- Access token sem invalidação pós-logout — `POST /auth/logout` agora
  também revoga o access token em uso (novo `jti` em todo token, nova
  tabela `revoked_access_tokens`), fechando a janela de até 30 minutos
  em que um token continuava aceito depois do logout.
- Rate limiting só por IP — nova segunda dimensão por usuário
  autenticado/alvo submetido (e-mail no login, token no
  refresh/2FA), que não pode ser contornada variando o IP de origem;
  limite mais agressivo (5 vs. 10 por minuto) especificamente para
  login/refresh/segundo fator.

**5 itens verificados e já corretos** (CORS, headers de segurança,
exposição de PII nas respostas, demais aspectos de JWT, enumeração de
usuários, SQL injection, IDOR) — confirmados por leitura do código
atual, não assumidos de auditorias anteriores.

Validado: `pytest` (14, incluindo 8 testes novos: rate limit ativo,
token rejeitado pós-logout, IDOR bloqueado, headers de segurança
presentes), requisições HTTP reais contra o backend local, `tsc -b` e
`npm run build` do frontend (sem mudança de código necessária lá).
Nenhuma mudança quebra contrato de API existente.

## 2026-07-22 - Separação Fluxo 1/Fluxo 2 na criação de post (conteúdo compartilhado vs. independente por conta)

Pedido explícito do usuário, após analisar criticamente que a
Publicação Inteligente vinha sendo usada como uma forma "escondida" de
criar tweets completamente diferentes por conta (editando as variações
até ficarem todas distintas), mesmo essa nunca tendo sido a proposta da
funcionalidade. Detalhe completo em `docs/ROADMAP_COMPOSICAO_POST.md`.

**Fluxo 1 (`composition_mode=shared`, default):** exatamente como já
era — um texto original, Publicação Inteligente opcional/obrigatória
por faixa de contas, mídia compartilhada.

**Fluxo 2 (`composition_mode=independent`, novo):** sem texto
principal, sem Publicação Inteligente — cada conta selecionada ganha
seu próprio editor desde o início, com mídia compartilhada (padrão) ou
individualizada por conta (`PostMedia.post_account_id`, novo,
nullable). `Post.text` fica `NULL` nesse modo; cada
`PostAccount.rendered_text` é obrigatório e independente das demais
(duplicar texto entre contas é permitido, decisão manual do usuário).

**Aviso de conteúdo duplicado (não bloqueia), adicionado nos dois
fluxos** após uma auditoria de segurança dedicada apontar que o Fluxo 2
contornava a proteção anti-detecção de conteúdo repetitivo (hoje só
aplicada obrigatoriamente a partir de 5 contas no Fluxo 1): quando 2+
contas ficam com o mesmo texto fora desse caso já bloqueado, a
interface avisa do risco de detecção pela plataforma X, mas permite
confirmar — bloquear automaticamente reverteria decisões de produto já
tomadas (variação é opcional em poucas contas; o Fluxo 2 dá controle
manual total ao usuário).

## 2026-07-22 - Coleta decrescente de métricas por idade do post (~45% menos leituras pagas)

Pedido explícito do usuário, depois de refletir sobre o custo agregado
da coleta de métricas na API do X (paga por uso). Detalhe completo em
`docs/ROADMAP_METRICAS.md`.

Antes, todo post dentro da janela de retenção (14 dias) era recoletado
na mesma frequência fixa (6h) do primeiro ao último dia — pagando pela
mesma leitura de um post de 10 dias (que já estabilizou) quanto de um
publicado há 2 horas. Agora a frequência decai com a idade do post:
≤72h → a cada 12h; até 7 dias → a cada 24h; depois disso, um último
snapshot ("final") e nunca mais — o número exibido ao cliente nunca
fica desatualizado de forma perceptível, porque já tinha estabilizado
antes do corte.

Mesma ideia aplicada aos seguidores de contas sem post publicado via
XHub há 30+ dias: em vez de continuar coletando 4x/dia uma conta
parada, cai para 1x/semana — **sem parar por completo** (ajuste
deliberado sobre a proposta original: parar de vez faria o número
congelar indefinidamente para uma conta que só está sem postar por um
tempo, não desconectada; volta ao normal automaticamente no próximo
post).

## 2026-07-22 - Segundo fator de login (pergunta de segurança) + reforço operacional pós-deploy

Pedido explícito do usuário após o deploy em produção, refletindo sobre
o que mais precisava de atenção operacional. Detalhe completo em
`docs/AUDITORIA_SEGURANCA.md`.

**Segundo fator de login (pergunta de segurança)** — hoje restrito a
administradores, opcional (login continua em uma etapa até ser
configurado). Fluxo: `POST /auth/login` retorna um `pending_token` (JWT
de 5 minutos, claim `stage: pending_2fa`) em vez do par de tokens
normal quando o usuário tem pergunta configurada; `POST
/auth/verify-security-answer` troca a resposta correta pelo par de
tokens real. O ponto crítico de segurança: `pending_token` é
explicitamente rejeitado por `get_current_user` (e por toda rota que
dependa dele) — sem essa checagem, o token pendente funcionaria como
bypass de autenticação completo. Resposta normalizada (case/espaço)
antes de comparar via hash bcrypt (reaproveita `app/auth/password.py`,
o mesmo usado para senha de conta). Configurável em
Configurações → "Segundo fator de login".

**Backup off-site criptografado** — o `pg_dump` diário (já existente)
passou a ser criptografado com GPG (simétrico, AES256) antes de sair do
disco e enviado por e-mail (Gmail SMTP via `msmtp`/`mutt`) para
`xhubplatform@gmail.com`, além da cópia local de 14 dias já existente.
A senha de descriptografia vive só em `/root/secrets/` na VPS **e**
fora dela (o administrador guardou uma cópia em local seguro) — se
guardasse só na VPS, perder a VPS tornaria os e-mails de backup
inúteis.

**Rotação de logs do Docker** — `docker-compose.prod.yml` ganhou
`logging: driver: json-file` com `max-size: 10m`/`max-file: 5` em
`db`/`backend` (sem limite antes, risco de encher o disco ao longo do
tempo). Logs do próprio Nginx já tinham rotação (pacote padrão do
Ubuntu, 14 dias, comprimido) — confirmado, nenhuma mudança necessária.

**Monitoramento** — watchdog local (`/opt/xhub/watchdog.sh`, cron a
cada 5 minutos) checa containers essenciais rodando, healthcheck do
backend, o site público via HTTPS e uso de disco, alertando por e-mail
(sem repetir o mesmo alerta enquanto o problema persistir). É um
backstop, não um substituto: se a VPS inteira cair, o watchdog para
junto — por isso a recomendação de também usar um serviço externo
gratuito (ex.: UptimeRobot) apontando para `https://xhub.app.br`.

**Tradução automática** — avaliada, não implementada como widget: o
`<html lang="pt-BR">` já existente ativa a tradução nativa do
Chrome/Edge sem nenhuma mudança de código. O widget clássico do Google
Translate exigiria afrouxar a CSP (`script-src` liberando
`unsafe-inline`/`unsafe-eval` e domínios do Google) — trade-off de
segurança considerado desnecessário dado que a tradução nativa já
cobre a maioria dos navegadores.

## 2026-07-22 - Deploy de produção (xhub.app.br) + correção de bypass de rate limit

Primeiro deploy real em VPS própria. Detalhe completo em
`deploy/README.md`. Infraestrutura: Ubuntu 24.04 LTS, firewall (só 22/
80/443), SSH só por chave, Docker Compose de produção
(`docker-compose.prod.yml`, sem os atalhos de desenvolvimento —
Postgres sem porta publicada, backend só em 127.0.0.1), Nginx como
reverse proxy + TLS (Let's Encrypt, renovação automática) + servindo o
build estático do frontend, backup diário automático do Postgres.

**Vulnerabilidade real encontrada e corrigida numa auditoria de
segurança pós-deploy pedida pelo usuário** (detalhe completo em
`docs/AUDITORIA_SEGURANCA.md`): o Nginx configurado inicialmente
*acrescentava* o IP real ao header `X-Forwarded-For` em vez de
sobrescrevê-lo, permitindo que um atacante contornasse completamente o
rate limit de login apenas forjando esse header a cada tentativa —
confirmado ao vivo (20 tentativas com IPs forjados diferentes, 0
bloqueadas antes da correção). Corrigido sobrescrevendo o header com o
IP real da conexão TCP; revalidado ao vivo (10 de 20 bloqueadas,
exatamente o limite configurado). Nenhuma mudança de código da
aplicação foi necessária — só a configuração do Nginx.

Confirmado sem outros achados: SQL injection (payloads clássicos
tratados como dado comum), ausência de vazamento de stack trace,
`DEBUG=false` efetivo, portas internas (backend/Postgres) inalcançáveis
de fora.

## 2026-07-22 - Site público de marketing (landing, sobre, contato, FAQ, legal)

Pedido explícito do usuário, antes do lançamento em produção (domínio já
adquirido): página principal pública com hero, funcionalidades e "como
funciona"; páginas de Sobre, Contato (xhubplatform@gmail.com), FAQ,
Política de Privacidade e Termos de Uso. Sem cadastro público — "Criar
conta" leva para a página de Contato, refletindo a regra real de que
toda conta é criada por um administrador.

A raiz do site (`/`) deixou de ser a home autenticada e virou a landing
page pública; a home autenticada foi renomeada para `/dashboard` (todos
os redirects/links internos atualizados). Novo `MarketingLayout`,
totalmente público, sem sidebar nem dependência de sessão.

**Auditoria de segurança da página nova, pedida junto:** encontrado e
corrigido um bug real de regressão — o redirect do callback OAuth do X
(`GET /oauth/x/callback`) apontava para a raiz do frontend, que antes
era a tela autenticada de contas conectadas; com a raiz virando a
landing pública, o retorno de sucesso/erro da conexão deixaria de
aparecer para o usuário. Corrigido para redirecionar especificamente
para `/accounts`. Restante da auditoria: sem XSS (nenhum
`dangerouslySetInnerHTML`/`innerHTML`), sem nova superfície de API
(contato é só `mailto:`, sem formulário com backend), sem segredo/dado
de teste vazado nas páginas novas, guarda de rotas íntegra (uma única
rota pública em `/`). Recomendação registrada para o deploy (fora do
escopo desta correção): headers de segurança do frontend em si
(CSP/X-Frame-Options) devem ser configurados no proxy reverso/hospedagem
estática, não via `<meta>` (que não cobre `frame-ancestors` e arriscaria
quebrar o HMR do Vite em desenvolvimento).

Validado: `tsc -b`/`npm run build` limpos, `pytest` sem regressão,
redirect do OAuth confirmado ao vivo apontando para `/accounts`.

## 2026-07-22 - Métricas de desempenho ("Resultados")

Nova funcionalidade pedida explicitamente pelo usuário: tela de
Resultados mostrando impressões, curtidas, respostas, republicações e
seguidores por conta do X conectada, com tendência vs. período anterior
e alerta automático quando o alcance de uma conta cai significativamente
em relação ao histórico dela mesma. Detalhe completo em
`docs/ROADMAP_METRICAS.md`.

Coleta roda em background (mesmo `BackgroundScheduler` já usado para
agendamento de posts, sem infraestrutura nova), limitada a posts
publicados nos últimos 14 dias por padrão — a API do X é paga por uso,
diferente de publicar, então a janela de coleta controla o custo
agregado. Duas tabelas novas, append-only (`account_metric_snapshots`,
`post_metric_snapshots`), mesmo princípio do `AuditLog`. Deliberadamente
sem a peça de encurtador de link/rastreio de clique discutida junto —
adiada por conflitar com a regra de imutabilidade de URL já existente
(`app.domain.content_invariants`).

Validado com 20 asserções (script descartável, dublê de `XOAuthClient`,
nunca a API real do X), `pytest` sem regressão, migration real aplicada,
rotas testadas ao vivo (IDOR, portfólio vazio, headers de segurança
intactos), `tsc`/`build` do frontend limpos.

## 2026-07-17 - Atualização de fastapi/starlette (CVEs corrigidos)

Item que a auditoria de segurança tinha deixado como recomendação para
depois (mudança de framework de maior superfície) — executado a pedido
explícito do usuário, com autorização para corrigir qualquer regressão
encontrada. `fastapi` 0.115.6→0.136.0, resolvendo `starlette` para
1.3.1 (a mais recente disponível), eliminando os 7 CVEs conhecidos
documentados em `docs/AUDITORIA_SEGURANCA.md`. Nenhuma regressão
encontrada: suíte completa, headers de segurança, CORS, rate limiting
em rota dinâmica, limite de corpo, handler de exceção e redirect do
OAuth do X revalidados um por um após o rebuild — todos idênticos ao
comportamento anterior. `pip-audit`: 34 → 9 vulnerabilidades conhecidas
restantes (todas já documentadas como risco aceito).

## 2026-07-17 - Correção: endpoint STATUS de upload de mídia (404 real)

Bug real encontrado ao testar publicação de vídeo com a conta do X
reconectada do usuário: `GET /2/media/upload/{id}/status` (usado para
aguardar o processamento assíncrono de gif/vídeo) retornava `404`. A
documentação oficial do X confirma que, ao contrário de
`initialize`/`append`/`finalize` (caminhos dedicados v2), `STATUS`
continua no padrão legado v1.1 — via query string no endpoint base
(`GET /2/media/upload?command=STATUS&media_id={id}`). Corrigido em
`app/oauth/oauth_client.py`. Detalhe completo em
`docs/ROADMAP_MEDIA.md`/`backend/CHANGELOG.md`. Validado: `pytest`
sem regressão, URL final conferida byte a byte contra a documentação
oficial.

## 2026-07-17 - Auditoria completa de segurança

Última auditoria do projeto antes de produção — ponta a ponta,
considerando um atacante com acesso apenas ao frontend/API pública.
Relatório técnico completo em `docs/AUDITORIA_SEGURANCA.md`. A maior
parte das áreas auditadas (autenticação, OAuth, autorização/IDOR, banco
de dados, frontend, backend, Docker, scheduler, integrações externas)
foi aprovada sem necessidade de correção. 5 vulnerabilidades reais
encontradas e corrigidas (nenhuma Crítica):

1. Ausência total de headers de segurança HTTP (`X-Frame-Options`,
   `Content-Security-Policy`, `X-Content-Type-Options`,
   `Referrer-Policy`, `Strict-Transport-Security`) — novo
   `SecurityHeadersMiddleware`.
2. Rate limiting cobria apenas `/auth/login`, deixando sem proteção
   endpoints com custo real de abuso (geração de preview da Publicação
   Inteligente, upload de mídia, publicação, agendamento, início de
   OAuth) — `RateLimitMiddleware` estendido.
3. Listas sem limite de tamanho em `twitter_account_ids`
   (`POST /posts`, `POST /intelligent-publication/preview`) permitiam
   DoS síncrono via lista enorme de UUIDs — `max_length` adicionado,
   derivado do maior plano do catálogo oficial.
4. Nenhum limite de tamanho de corpo de requisição JSON — novo
   `BodySizeLimitMiddleware` (413 acima de 1 MiB, exceto multipart).
5. Enumeração de e-mails cadastrados por análise de tempo de resposta
   do login (bcrypt só era chamado quando o e-mail existia) —
   mitigado com verificação de hash "isca" em tempo constante.

Dependências: `pip-audit` encontrou 34 vulnerabilidades conhecidas em 8
pacotes; `cryptography`, `python-jose`, `python-multipart` e
`python-dotenv` atualizados (16 delas corrigidas). As demais foram
avaliadas individualmente e documentadas como risco aceito (código
vulnerável nunca exercitado pelo uso real da aplicação, ou fora da
superfície de ataque) ou como recomendação para a próxima etapa
(`fastapi`/`starlette`, mudança de framework de maior superfície, fora
do escopo desta correção pontual).

Validado: `pytest` sem regressão em cada rebuild da imagem, roundtrip
real de `Fernet`/JWT nas novas versões de `cryptography`/`python-jose`,
simulação de flood ao vivo confirmando `429` nos endpoints estendidos,
`413`/`422` confirmados para payload/lista gigantes, `npm audit`
(frontend) sem nenhuma vulnerabilidade conhecida.

## 2026-07-17 - Custo de publicação por link (15 créditos/conta)

Regra de negócio pedida explicitamente pelo usuário logo após a
auditoria funcional (que havia identificado esta função como não
implementada e deliberadamente fora de escopo naquela etapa — ver
`docs/AUDITORIA_FUNCIONAL.md`). Implementada e validada nesta etapa.
Relatório técnico completo em `docs/ROADMAP_CUSTO_LINK.md`.

Regra: post cujo texto contém pelo menos um link consome **15
créditos por conta publicada**; qualquer outro post (texto simples ou
com mídia anexada, sem link) continua consumindo **1 crédito por
conta**, comportamento já existente antes desta mudança. Mídia nunca
altera o custo — só a presença de link no texto.

`app/domain/publication_cost.py` (código preparatório já existente,
nunca conectado ao fluxo real) foi reescrito para refletir a regra real
(binária: link ou não, independente de mídia) em vez do modelo antigo
de classificação mutuamente exclusiva TEXT/IMAGE/VIDEO/LINK, que não
correspondia à realidade (um post pode ter mídia e link ao mesmo tempo).
`PostService.publish_post` agora calcula o custo por conta uma única
vez por post e usa esse valor tanto na validação de saldo suficiente
(antes de qualquer chamada ao X) quanto no consumo efetivo por conta
publicada com sucesso. Frontend ganhou um aviso visível no compositor
de posts quando o texto contém um link, mostrando o custo real antes de
publicar.

Validado: `pytest` sem regressão (6/6), `tsc`/`build` limpos, e um
script descartável confirmando detecção de link, consumo de 1 vs. 15
créditos por conta, bloqueio de saldo insuficiente antes de qualquer
chamada ao X, e independência do custo em relação à mídia anexada.

## 2026-07-17 - Auditoria funcional completa

Validação de ponta a ponta de todo o sistema (autenticação, admin,
publicações, Publicação Inteligente, mídia, consumo/limites, scheduler,
banco de dados, frontend, backend, escalabilidade), antes da auditoria
de segurança final. Relatório técnico completo em
`docs/AUDITORIA_FUNCIONAL.md`. Sete problemas reais encontrados e
corrigidos na causa raiz (nenhuma funcionalidade nova):

1. Login não bloqueava usuário bloqueado (`AuthService.authenticate`).
2. Mensagem/status inconsistentes ao renovar sessão de usuário
   bloqueado (`AuthService.rotate_refresh_token`).
3. `routes/auth.py` não mapeava `ForbiddenException` para HTTP 403.
4. Post publicado podia ser excluído, apagando o histórico real de
   publicação (`PostService.delete_post` + `PostsPage.tsx`).
5. Texto do diálogo de desconexão de conta do X induzia a erro sobre o
   que acontece com o histórico de publicações (`AccountsPage.tsx`).
6. `pytest` ausente de `backend/requirements.txt` — suíte não rodava
   em uma imagem construída do zero.
7. Teste `test_get_subscription_returns_subscription_for_admin`
   desatualizado (dublê incompleto) — falhava desde uma feature
   anterior; agora corrigido.

Validado com `pytest` (6 passaram, 0 falharam — primeira vez com a
suíte inteiramente verde), `tsc --noEmit`/`npm run build` limpos, e um
script descartável com 40 asserções de regra de negócio (nunca tocando
a API real do X/Groq). Itens pré-existentes conhecidos (custo
diferenciado por tipo de conteúdo não implementado, algumas ações de
auditoria não disparadas, publicação imediata síncrona) permanecem
documentados e deliberadamente não alterados — corrigi-los exigiria
implementar funcionalidade nova, fora do escopo desta auditoria.

## 2026-07-16 - Atualizacao completa da documentacao oficial

Auditoria completa do codigo atual (backend e frontend) seguida de reescrita
da documentacao oficial, tratando o codigo como fonte da verdade. Nenhuma
funcionalidade foi alterada nesta tarefa -- apenas documentacao.

### Arquivos criados

- `claude.md`
  - Contexto tecnico completo do projeto para IA: objetivo, arquitetura,
    camadas, convencoes, regras de negocio, fluxos (autenticacao, OAuth,
    publicacao, Publicacao Inteligente, midia, scheduler, Jitter, painel
    administrativo), entidades principais, decisoes arquiteturais e uma
    lista explicita de dividas tecnicas/lacunas conhecidas (para nao serem
    "redescobertas" nem corrigidas sem pedido explicito).

### Arquivos reescritos

- `README.md`
  - Reescrito por completo para refletir o estado atual do XHub: todas as
    funcionalidades implementadas (autenticacao, primeiro acesso
    obrigatorio, painel administrativo, planos/assinaturas, OAuth do X,
    multiplas contas, Publicacao Inteligente/Groq, upload e edicao de
    midia, scheduler, Jitter, auditoria), stack, estrutura de pastas
    atualizada, variaveis de ambiente e instrucoes de execucao local/Docker.
    A versao anterior so documentava o estado do backend em 2026-07-09,
    antes de Midia, Primeiro Acesso, Publicacao Inteligente e Jitter
    existirem.

### Arquivos atualizados

- `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`
  - **Inconsistencia corrigida**: o arquivo ainda se apresentava como
    "especificacao oficial para implementacao futura" e listava a
    funcionalidade inteira como nao implementada ("Nao existe cliente
    Groq", "Nao existe endpoint de preview", etc.), mas o codigo atual ja
    implementa e valida a funcionalidade por completo (`GroqClient`,
    `AIContentVariationService`, `PostAccount.rendered_text`, endpoint de
    preview, modal de edicao no frontend). Atualizado para o mesmo formato
    de `docs/ROADMAP_MEDIA.md`/`ROADMAP_PRIMEIRO_ACESSO.md`/
    `ROADMAP_JITTER.md`: titulo, "Estado atual relevante", nova secao
    "Arquitetura implementada" (mapeamento arquivo a arquivo do que
    realmente existe) e "Validacao realizada".
- `.continue/context/XHUB_CONTEXT.md`
  - Reescrito para refletir o estado de 2026-07-16 (estava descrevendo o
    estado de 2026-07-09). Passa a apontar `claude.md` como fonte primaria
    de contexto tecnico detalhado.
- `.continue/context/ROADMAP.md`
  - Secoes "Planejado/especificado" e "Nao implementado" moviam Publicacao
    Inteligente, Midia, Primeiro Acesso e Jitter para fora do que ja existe
    no codigo -- corrigido: essas quatro funcionalidades agora aparecem em
    "Implementado conforme codigo atual"; a secao "Nao implementado" foi
    reduzida ao que de fato ainda nao existe (custo por tipo de conteudo,
    cache persistido, algumas acoes de auditoria nao disparadas, testes
    automatizados mais profundos).

### Inconsistencias encontradas e como foram corrigidas

1. `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md` descrevia a funcionalidade como
   nao implementada; o codigo (`app/services/ai_content_variation_service.py`,
   `app/integrations/groq_client.py`, `app/routes/intelligent_publication.py`,
   frontend em `components/intelligent-publication/`) mostra que esta
   completa e funcional. Corrigido reescrevendo o documento no formato
   "especificacao + estado implementado".
2. `.continue/context/XHUB_CONTEXT.md` e `.continue/context/ROADMAP.md`
   descreviam um snapshot de 2026-07-09, anterior a quatro funcionalidades
   inteiras (Midia, Primeiro Acesso, Publicacao Inteligente, Jitter).
   Corrigido com reescrita completa de ambos.
3. `README.md` nao mencionava nenhuma das funcionalidades acima, ainda
   descrevia fluxo de publicacao sem Jitter/midia/variacao de texto, e a
   estrutura de pastas nao incluia `domain/`, `integrations/`, `schemas/`
   nem os modulos novos. Corrigido com reescrita completa.
4. Nenhuma inconsistencia foi encontrada entre `docs/ROADMAP_MEDIA.md`,
   `docs/ROADMAP_PRIMEIRO_ACESSO.md`, `docs/ROADMAP_JITTER.md` e o codigo
   atual -- os tres ja estavam no formato "especificacao + estado
   implementado" e foram usados como referencia de estilo para as demais
   correcoes.

## 2026-07-09 - Base Continue.dev e especificacao da Publicacao Inteligente

### Arquivos criados

- `.continue/README.md`
  - Explica a estrutura da base de conhecimento permanente do projeto para
    Continue.dev.

- `.continue/rules/01-xhub-core.md`
  - Regras globais que devem ser aplicadas pela IA em qualquer tarefa no XHub.

- `.continue/rules/02-backend-python.md`
  - Regras especificas para arquivos Python do backend.

- `.continue/rules/03-frontend-react.md`
  - Regras especificas para arquivos TypeScript/React/CSS do frontend.

- `.continue/context/XHUB_CONTEXT.md`
  - Contexto tecnico permanente do projeto: produto, arquitetura, banco,
    autenticacao, APIs, integracoes, decisoes e riscos.

- `.continue/context/ROADMAP.md`
  - Roadmap permanente para IA, com estado implementado, planejado, nao
    implementado e divergencias conhecidas. Deve receber o roadmap oficial
    quando o arquivo Markdown for fornecido.

- `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`
  - Especificacao oficial da funcionalidade Publicacao Inteligente para
    implementacao futura por outra IA ou desenvolvedor.

- `CHANGELOG.md`
  - Registro desta preparacao, com motivo de cada arquivo e orientacao de uso
    futuro.

### Arquivos alterados

- `README.md`
  - Corrigido para refletir o estado real observado no codigo atual.
  - A versao anterior estava desatualizada e indicava que ainda nao existiam
    rotas, repositories e services, mas o backend atual ja possui essas camadas.

### Como a implementacao futura deve usar estes arquivos

- Antes de implementar qualquer funcionalidade, anexar ou abrir
  `.continue/context/XHUB_CONTEXT.md`.
- Para Publicacao Inteligente, usar
  `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md` como especificacao principal.
- Atualizar `.continue/context/ROADMAP.md` sempre que o roadmap oficial mudar.
- Manter as regras em `.continue/rules` curtas e prescritivas; contexto longo
  deve permanecer em `.continue/context`.
