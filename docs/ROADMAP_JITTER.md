# Jitter - Especificacao e estado implementado

Este documento registra a especificacao oficial e o estado JA
IMPLEMENTADO do sistema de Jitter do XHub, seguindo o mesmo formato de
`docs/ROADMAP_MEDIA.md`, `docs/ROADMAP_PRIMEIRO_ACESSO.md` e
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`. Trate o codigo como fonte da
verdade em caso de divergencia futura.

## Objetivo

Reduzir padroes automatizados durante a publicacao em multiplas
contas do X. O objetivo nao e apenas adicionar um atraso aleatorio --
e tornar a SEQUENCIA de publicacoes menos robotica: quando um post e
publicado em varias contas, cada publicacao (a partir da segunda)
espera um tempo aleatorio antes de ocorrer.

## Regras de negocio oficiais

- O Jitter so se aplica quando ha MAIS DE UMA conta sendo publicada
  NESTA chamada (`accounts_to_publish` -- ja excluindo contas
  `PUBLISHED` anteriormente). Se so houver uma conta pendente -- seja
  porque o post tem uma unica conta, seja porque e um RETRY com as
  demais ja publicadas --, nenhum atraso e aplicado.
- Nunca aplicado antes da primeira publicacao do lote.
- Aplicado ENTRE uma publicacao e a proxima: publica na conta 1 (sem
  atraso) -> aguarda -> publica na conta 2 -> aguarda -> publica na
  conta 3 -> ... ate a ultima.
- Cada atraso e sorteado independentemente (distribuicao uniforme
  entre o minimo e o maximo configurados) -- nunca reaproveita o valor
  de uma amostragem anterior.
- Falha em uma conta NAO interrompe o Jitter das demais -- o atraso
  continua sendo aplicado antes de cada tentativa seguinte, com ou sem
  falha na anterior.

## Configuracao

Centralizada e editavel pelo administrador em tempo real, sem
alteracao de codigo nem reinicio da aplicacao:

- `JitterSettings` (tabela `jitter_settings`, singleton -- sempre
  exatamente uma linha): `min_seconds`, `max_seconds` (float,
  segundos).
- Valores padrao (`settings.JITTER_DEFAULT_MIN_SECONDS=1.5`,
  `JITTER_DEFAULT_MAX_SECONDS=8.0`) usados APENAS como seed da linha
  singleton na primeira leitura (ver
  `JitterSettingsRepository.get_or_create_default`).
- Teto de seguranca (`settings.JITTER_MAX_ALLOWED_SECONDS=120.0`):
  evita que um valor digitado por engano (ex.: 600 em vez de 6.0)
  torne uma publicacao em varias contas absurdamente lenta a ponto de
  estourar timeout do navegador/proxy na chamada sincrona de
  `POST /posts/{id}/publish`.
- Painel administrativo: `PATCH /admin/jitter-settings` (tela
  dedicada "Jitter" no menu administrativo) -- toda alteracao vale
  IMEDIATAMENTE para a proxima publicacao, pois `JitterService`
  sempre le o valor atual do banco a cada chamada (nunca cacheado em
  memoria).

## Arquitetura implementada

Preserva a arquitetura em camadas do XHub (`Routes -> Services ->
Repositories -> Models`), seguindo o mesmo padrao ja usado para outras
configuracoes singleton/administrativas deste projeto.

### Backend

- `app/domain/jitter.py`
  - `sample_jitter_delay_seconds(min_seconds, max_seconds) -> float`:
    funcao PURA (sem I/O, sem `time.sleep`) -- amostra por
    `random.uniform`. Mesmo padrao de `app.domain.media_rules`/
    `app.domain.content_invariants`.
- `app/models/jitter_settings.py` (`JitterSettings`)
  - Tabela singleton -- sempre uma unica linha.
- `app/repositories/jitter_settings_repository.py`
  - `get_or_create_default()`: cria a linha com os valores padrao na
    primeira leitura, se ainda nao existir.
- `app/services/jitter_service.py` (`JitterService`)
  - `get_settings()` / `update_settings(min_seconds, max_seconds)`
    (valida min>=0, max>=min, max<=teto) / `apply_delay(...)` --
    UNICO lugar do codigo que efetivamente aguarda (`time.sleep`) e
    registra o log. Nunca decide QUANDO aplicar (isso e
    responsabilidade de quem chama, `PostService.publish_post`, que
    conhece o contexto de negocio da publicacao).
- `app/services/post_service.py` (`PostService.publish_post`)
  - Loop `for account_index, post_account in enumerate(accounts_to_publish)`:
    se `account_index > 0`, chama `jitter_service.apply_delay(...)`
    ANTES de qualquer efeito colateral da proxima conta (token, upload
    de midia, chamada de publicacao) -- exatamente onde a spec pede
    ("aplicar o atraso; publicar na proxima"). Nenhuma outra parte da
    funcao foi alterada: idempotencia, validacoes de negocio
    (assinatura/saldo), tratamento de falha, commits individuais por
    conta e o fluxo da Publicacao Inteligente/midia continuam
    identicos.
- `app/routes/admin.py`
  - `GET /admin/jitter-settings`, `PATCH /admin/jitter-settings` --
    audita `AuditAction.JITTER_SETTINGS_UPDATED` (nunca com dados
    sensiveis, so os valores min/max escolhidos).
- Migrations: `e5f6a7b8c9d0` (cria `jitter_settings`, sem seed --
  seed acontece sob demanda na primeira leitura) e `f6a7b8c9d0e1`
  (`AuditAction.JITTER_SETTINGS_UPDATED` no enum nativo do Postgres).
- `app/scheduler.py`
  - `_publish_claimed_post` injeta `JitterService` na construcao
    manual de `PostService` (mesmo ponto onde `post_media_repository`
    ja era injetado) -- publicacao AGENDADA usa o MESMO
    `PostService.publish_post`, portanto o MESMO Jitter, sem nenhuma
    logica adicional no worker.

### Frontend

- `types/jitter.ts`, `services/jitter.ts`,
  `hooks/useAdminJitterSettings.ts`: tipos, chamadas HTTP e hooks
  (`useJitterSettings`/`useUpdateJitterSettings`), mesmo padrao de
  `hooks/useAdminPlans.ts`.
- `pages/AdminJitterSettingsPage.tsx`: tela dedicada ("Jitter" no menu
  administrativo, `components/layout/Sidebar.tsx`), mesmo padrao
  visual de `AdminPlansPage.tsx` -- formulario com "Tempo mínimo
  (segundos)"/"Tempo máximo (segundos)", validado no cliente
  (espelhando as mesmas regras do backend) antes de enviar.
- Nenhuma alteracao na experiencia do cliente final -- o Jitter e
  inteiramente transparente para quem publica.

## Log e auditoria

`JitterService.apply_delay` registra um log estruturado (JSON, mesmo
padrao de `app.core.logging_config`) a cada atraso aplicado:
`post_id`, `account_index`, `total_accounts`, `delay_seconds`. O valor
exato NAO e exposto em nenhuma resposta de API ao usuario final --
existe apenas neste log, para depuracao/auditoria tecnica.
`AuditAction.JITTER_SETTINGS_UPDATED` registra toda alteracao
administrativa da configuracao (quem, quando, novos valores).

## Decisoes tecnicas

**Por que `time.sleep` sincrono (nao assincrono):** o backend inteiro
e sincrono (nenhuma rota `async def`, todas as chamadas externas --
Groq, X, upload de midia -- ja usam `httpx.Client` bloqueante). Um
`time.sleep` dentro de `PostService.publish_post` (que roda em uma
thread do pool do FastAPI) e consistente com esse padrao existente e
nao exige introduzir `asyncio` em nenhum outro lugar.

**Por que a checagem e so `account_index > 0` (sem checar
`len(accounts_to_publish) > 1` separadamente):** matematicamente
equivalente e mais simples -- numa lista de 1 item, o indice nunca
passa de 0, entao a mesma condicao unica ja satisfaz as duas regras
("nunca antes da primeira" e "sem atraso se so houver uma conta") sem
duplicar a checagem.

**Por que a tabela `jitter_settings` e "singleton" (sempre uma linha)
em vez de usar `.env`:** a especificacao exige que a alteracao valha
para as PROXIMAS publicacoes sem mudanca de codigo nem reinicio --
variaveis de ambiente (`app.config.settings`) so sao lidas na
inicializacao do processo (`lru_cache` em `get_settings()`), o que
exigiria reiniciar a aplicacao a cada ajuste. Uma linha em banco,
sempre lida no momento da publicacao, satisfaz o requisito
diretamente, com o menor numero de conceitos novos possivel (nenhuma
tabela de "chave-valor" generica, nenhuma dependencia nova).

**Por que nao ha um "seed" inserido pela migration:** a logica de
"quais sao os valores padrao" ja vive em `app.config.settings`
(unico lugar) -- duplica-la na migration (como dado, nao como schema)
criaria duas fontes de verdade para o mesmo default. O
`get_or_create_default()` cria a linha com os valores atuais de
`settings` a primeira vez que alguem le a configuracao (seja o
publish_post, seja o GET do painel administrativo).

**Impacto no scheduler (analise explicita, por ser um requisito
proibido de comprometer):** `process_due_scheduled_posts` processa
todos os agendamentos vencidos de um tick SEQUENCIALMENTE, e so
comita a reivindicacao (`claim_db`, que mantem o lock
`FOR UPDATE SKIP LOCKED` das linhas de `scheduled_posts`) apos
processar TODOS os posts do lote. O Jitter aumenta o tempo total de
cada tick proporcionalmente ao numero de contas com mais de uma conta
por post -- isso e uma consequencia esperada e inerente ao proprio
objetivo da funcionalidade (pacing mais humano custa tempo de
parede), nao uma quebra de garantia: `max_instances=1` +
`coalesce=True` (ja configurados) garantem que um tick mais longo
nunca sobrepoe com o proximo, apenas atrasa o inicio dele -- sem
duplicar processamento nem perder agendamentos. Nenhuma mudanca na
logica de transacao/lock do scheduler foi necessaria ou feita.

## Validacao realizada

Ciclo completo testado via `curl` contra a API real e via scripts de
integracao com um `XOAuthClient` dublê (removidos apos validar, nunca
tocaram a API real do X):

1. `GET /admin/jitter-settings` (primeira leitura) -- cria a linha
   singleton com os valores padrao (1.5/8.0).
2. `PATCH` com `max < min` -- `422` com mensagem clara (regra de
   negocio).
3. `PATCH` com `min` negativo -- `422` (validacao Pydantic).
4. `PATCH` com `max` acima do teto de seguranca -- `422` com mensagem
   clara.
5. `PATCH` valido -- `200`, e `GET /admin/audit-logs` confirma
   `JITTER_SETTINGS_UPDATED` registrado (sem vazar nada sensivel).
6. Publicacao com **1 conta**: processada em ~0.05s -- **sem** nenhum
   atraso.
7. Publicacao com **4 contas** (com `rendered_texts` da Publicacao
   Inteligente): exatamente 3 intervalos entre as 4 publicacoes,
   todos dentro do range configurado (0.5-1.5s), todos com valores
   DISTINTOS entre si (confirma amostragem independente); cada conta
   recebeu seu texto correto (variacao, nao o original).
8. Publicacao com **midia real anexada** + 2 contas: upload de midia
   por conta + atraso entre publicacoes funcionando juntos sem
   conflito; `delete_post` removeu o arquivo do disco normalmente.
9. Publicacao **AGENDADA** (via `ScheduledPostService.claim_due` +
   `PostService.publish_post`, o mesmo caminho de
   `app/scheduler.py`) com midia + 2 contas: mesmo Jitter aplicado,
   mesmo comportamento da publicacao imediata.
10. Publicacao com **1 conta falhando** entre 3: Jitter continuou
    aplicado entre as tentativas mesmo com uma falha no meio; status
    por conta corretos (1 failed, 2 published); `error_message`
    preservado com o motivo exato.
11. **Retry** do post acima (so a conta que falhou ainda pendente, as
    outras 2 ja `PUBLISHED`): processado em ~0.01s -- **sem**
    nenhum atraso (regra "se existir apenas uma conta: nao aplicar
    atraso"), e as 2 contas ja publicadas NAO foram reprocessadas
    (idempotencia preservada).
12. `pytest`: 5 passaram, 1 falha pre-existente e nao relacionada
    (mesma de sessoes anteriores).
13. Frontend: `tsc --noEmit` e `npm run build` limpos; servidor de
    desenvolvimento verificado via `curl` apos restart (novos
    arquivos servidos, item "Jitter" no menu, rota registrada).

**Nao validado interativamente no navegador** (sem ferramenta de
automacao de browser disponivel neste ambiente) -- a tela
`AdminJitterSettingsPage` foi verificada apenas estaticamente (tipos,
build, arquivo servido corretamente). Recomenda-se um teste manual
clicando na interface antes de depender dela no dia a dia.

## Fora de escopo desta implementacao

- Qualquer outra funcionalidade alem do Jitter (instrucao explicita).
- Configuracao por usuario/plano (o Jitter e uma unica configuracao
  global da plataforma, nao pedida por usuario).
- Exposicao do valor exato do atraso para o cliente final em qualquer
  tela ou resposta de API (explicitamente nao pedido -- so log tecnico).
