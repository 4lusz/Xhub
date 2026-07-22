# Métricas de desempenho ("Resultados") — XHub

> Especificação + estado implementado (mesmo formato de
> `docs/ROADMAP_MEDIA.md`/`ROADMAP_JITTER.md`/`ROADMAP_CUSTO_LINK.md`).
> Feature pedida explicitamente pelo usuário após a auditoria de
> segurança, com o objetivo de dar visibilidade real de desempenho
> (impressões, curtidas, seguidores) por conta e por post, sem a peça
> de encurtador/rastreio de clique (deliberadamente adiada — ver seção
> "Fora de escopo").

## 1. Objetivo

Cliente entra na tela **Resultados** e vê, para cada conta do X
conectada: seguidores, impressões, curtidas, respostas e
republicações do período, com tendência (variação % vs. período
anterior) e um alerta quando o alcance de uma conta cai
significativamente em relação ao histórico dela mesma. Drill-down por
conta mostra o histórico de seguidores e os melhores posts; drill-down
por post mostra a curva completa de métricas desde a publicação.

## 2. Regra de negócio: por que a coleta é limitada e controlada

A API do X é **paga por uso** (diferente de publicar, já incluído no
custo do plano) — cada leitura de métrica tem custo direto. Por isso:

- Só posts publicados dentro de `METRICS_POST_RETENTION_DAYS` (padrão
  14 dias) continuam recebendo coleta nova — a maior parte do alcance
  de um post acontece nas primeiras 24-48h, então uma janela curta
  captura o essencial sem custo crescente indefinidamente. O **último**
  snapshot de um post que sai da janela nunca é apagado (append-only).
- Leitura de impressões (`organic_metrics.impression_count`) e demais
  métricas (`public_metrics`) de até 100 tweets **da mesma conta** são
  pedidas em uma única chamada (`XOAuthClient.get_tweet_metrics`) — nunca
  uma chamada por tweet.
- A anomalia de alcance compara uma conta **contra o próprio
  histórico**, nunca contra outra conta (volumes de audiência variam
  demais entre contas para essa comparação fazer sentido) — ver
  `app.domain.metrics.detect_reach_anomaly`.

## 3. Arquitetura implementada

- `app/domain/metrics.py` — funções puras (sem I/O): `compute_percent_change`
  (variação percentual entre dois valores) e `detect_reach_anomaly`
  (compara a média de impressões dos últimos N posts de uma conta
  contra a média do histórico anterior dela mesma; retorna
  `has_enough_data=False` em vez de alarmar sem base quando não há
  posts suficientes).
- `app/models/account_metric_snapshot.py` /
  `app/models/post_metric_snapshot.py` — duas tabelas append-only
  (mesmo princípio de `AuditLog`: `update`/`delete`/`delete_by_id`
  bloqueados nos repositories correspondentes, nunca sobrescrevem).
  `PostMetricSnapshot.twitter_account_id` é denormalizado a partir de
  `PostAccount.twitter_account_id` no momento da coleta — evita JOIN na
  consulta mais comum (portfólio por conta).
- `app/oauth/oauth_client.py` (`XOAuthClient`) — dois métodos novos:
  `get_account_metrics` (`GET /2/users/me?user.fields=public_metrics`,
  hoje só seguidores) e `get_tweet_metrics` (`GET /2/tweets?ids=...
  &tweet.fields=organic_metrics,public_metrics`, até 100 ids por
  chamada, usando o token OAuth da PRÓPRIA conta autora dos tweets —
  `organic_metrics.impression_count` exige contexto de usuário,
  diferente de `public_metrics`). Nunca falha só porque
  `organic_metrics` não está autorizado para o tier/app atual —
  `impression_count` volta `None` nesse caso, o resto continua normal.
  `_raise_for_media_error` foi renomeado para `_raise_for_x_api_error`
  (mapeamento de erro HTTP genérico, sempre foi independente de
  mídia — agora reaproveitado também pelos dois métodos novos).
- `app/services/metrics_service.py` (`MetricsService`) — duas frentes:
  - **Coleta** (`collect_all`): percorre TODA conta do X conectada na
    plataforma (de qualquer usuário), commit/rollback por conta (uma
    conta com falha nunca derruba a coleta das demais). Renova o token
    quando expirado (mesma lógica de
    `PostService._get_valid_access_token`, duplicada de propósito — ver
    comentário no código).
  - **Consulta** (`get_portfolio_summary`/`get_account_detail`/
    `get_post_account_detail`): sempre escopada ao usuário autenticado,
    posse verificada explicitamente (mesmo padrão de IDOR do resto do
    projeto).
- `app/scheduler.py` — novo job `collect_account_and_post_metrics` no
  MESMO `BackgroundScheduler` in-process já existente (nunca um
  worker/broker novo, ver claude.md seção de arquitetura), intervalo
  próprio (`settings.METRICS_COLLECTION_INTERVAL_SECONDS`, padrão 6h —
  bem mais espaçado que o do scheduler de posts, já que cada tick tem
  custo real na API do X).
- `app/routes/metrics.py` + `app/schemas/metrics.py` — três rotas,
  somente leitura: `GET /metrics/accounts` (portfólio, com
  `period_days` configurável), `GET /metrics/accounts/{id}` (histórico
  de seguidores + melhores posts), `GET /metrics/post-accounts/{id}`
  (curva completa de um post). Nenhuma rota de escrita — a coleta
  acontece exclusivamente no scheduler.
- `app/config/settings.py` — `METRICS_COLLECTION_ENABLED`,
  `METRICS_COLLECTION_INTERVAL_SECONDS`, `METRICS_POST_RETENTION_DAYS`,
  `METRICS_ANOMALY_LOOKBACK_DAYS`, `METRICS_ANOMALY_RECENT_WINDOW`,
  `METRICS_ANOMALY_MIN_TOTAL_POSTS`, `METRICS_ANOMALY_DROP_THRESHOLD`.
- Frontend: `types/metrics.ts`, `services/metrics.ts`,
  `hooks/useMetrics.ts`, `pages/ResultsPage.tsx` (portfólio, tabela com
  tendência e badge de anomalia, seletor de período 7/30 dias),
  `pages/AccountResultsDetailPage.tsx` (histórico de seguidores +
  melhores posts, com dialog mostrando a curva completa de um post ao
  clicar). Nova entrada "Resultados" no `Sidebar`. Sem biblioteca de
  gráficos nova — histórico apresentado em tabela/lista, consistente
  com o resto do projeto (que já usa tabelas extensivamente, nunca
  gráficos, ver `AdminPostsPage`).

## 4. Validação realizada

- Script Python descartável (criado, executado, apagado) com dublê de
  `XOAuthClient` (nunca a API real do X): 20 asserções cobrindo funções
  puras de domínio (`compute_percent_change`, `detect_reach_anomaly` em
  série estável/com queda/dado insuficiente), coleta end-to-end
  (snapshot de conta e de post gravados corretamente, incluindo o
  campo denormalizado), consulta de portfólio, bloqueio append-only
  (`update`/`delete` levantam `ConflictException`) e IDOR (usuário
  diferente não acessa conta/post de outro) — 20/20 passaram.
- `pytest` sem regressão (6/6) após a migration e o restart do backend.
- Migration real aplicada (`alembic upgrade head`,
  `f6a7b8c9d0e1 → a4b5c6d7e8f9`) contra o Postgres do ambiente de
  desenvolvimento.
- Rotas testadas ao vivo: portfólio vazio retorna `200 []` (sem conta
  conectada, sem erro); `404` para conta/post de outro usuário ou
  inexistente; `401` sem token; headers de segurança (auditoria
  anterior) continuam presentes nas novas rotas.
- `tsc -b` e `npm run build` do frontend limpos.
- **Limitação registrada:** sem ferramenta de automação de navegador
  disponível neste ambiente para clique-a-clique visual (mesma
  limitação já registrada em validações anteriores do projeto) — a
  tela foi revisada por completo no código (estados de loading, vazio,
  navegação) e o servidor de desenvolvimento confirmado servindo as
  novas rotas sem erro, mas não houve confirmação visual em navegador
  real.
- **Não foi possível validar contra a API real do X nesta etapa**
  (a coleta só roda em background, no intervalo configurado, e este
  ambiente não tem uma conta do X reconectada com posts recentes no
  momento da validação) — a suposição sobre o formato de resposta de
  `organic_metrics`/`public_metrics` segue a documentação oficial
  (`docs.x.com/x-api/fundamentals/metrics`), mas, seguindo o mesmo
  princípio já registrado para o upload de mídia (`ROADMAP_MEDIA.md`),
  deve ser confirmada na primeira coleta real.

## 5. Fora de escopo desta implementação

- **Encurtador de link com rastreio de clique** (proposto durante a
  discussão da feature): exigiria reescrever a URL que o usuário
  digitou antes de publicar, o que contradiz a regra de imutabilidade
  de URL já imposta por `app.domain.content_invariants`
  (`preserves_invariants`) e pelo prompt da Publicação Inteligente.
  Decisão de produto explicitamente adiada até ser tomada com clareza
  sobre essa troca — não implementado.
- Normalização por dia da semana/horário na detecção de anomalia (só
  reduziria falso-positivo de padrões semanais previsíveis, ex. queda
  toda segunda de manhã) — refinamento possível, não crítico para a
  primeira versão.
- Relatório PDF exportável / white-label para a agência mostrar ao
  cliente final dela — mencionado como próximo passo natural (as
  mesmas queries já existem), não implementado nesta etapa.
- Cota de armazenamento por usuário para as tabelas de série histórica
  — mesmo trade-off já aceito para outras tabelas de crescimento
  contínuo do projeto (`AuditLog`); revisar se o volume real justificar
  particionamento (Postgres puro aguenta um volume considerável antes
  disso ser necessário).
