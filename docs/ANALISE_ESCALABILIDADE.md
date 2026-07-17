# Análise de escalabilidade — clientes com muitas contas conectadas

Este documento registra uma análise arquitetural (leitura de código e
raciocínio sobre concorrência/transações, **sem testes de carga
artificiais**) sobre se o XHub suporta com segurança clientes com 10,
20, 50 e 100 contas conectadas (o teto real do plano "Agência", o maior
do catálogo — `app/domain/plans.py`). Encomendada antes da auditoria
funcional e de segurança final do projeto.

## Metodologia

Leitura completa do caminho de publicação (`PostService.publish_post`),
do worker de agendamento (`app.scheduler`), do serviço de Publicação
Inteligente (`AIContentVariationService`/`GroqClient`), do cliente HTTP
do X (`XOAuthClient`), da configuração de pool de conexões do banco
(`app/database/session.py`) e das rotas relevantes, seguida de
raciocínio sobre o que acontece quando o número de contas de um único
post cresce de 1 para 100. Nenhum benchmark sintético foi executado —
os problemas abaixo foram identificados pela leitura do código, não
por medição sob carga fabricada. As correções foram validadas com
scripts descartáveis usando dublês (nunca a API real do X/Groq),
seguindo o mesmo padrão já usado neste projeto para as demais
funcionalidades.

## Resumo do veredito

| Área | Com 10–20 contas | Com 50–100 contas (antes) | Depois da correção |
|---|---|---|---|
| Concorrência/idempotência de publicação | OK | OK | OK (sem mudança necessária) |
| Banco de dados / pool de conexões | OK | OK (ver ressalva do scheduler) | OK |
| Scheduler (agendamento) | OK | **Gargalo real** | Corrigido |
| Publicação Inteligente / Groq | OK | **Risco real** | Corrigido |
| Chamadas HTTP à API do X | OK | Ineficiente, não incorreto | Corrigido |
| Upload de mídia (memória) | OK | OK | OK (sem mudança necessária) |
| Publicação imediata síncrona (`POST /posts/{id}/publish`) | OK | **Risco residual aceito** | Não alterado — ver seção final |

## 1. Concorrência e idempotência — sem gargalo

`PostService.publish_post` já commita cada `PostAccount` individualmente
e imediatamente após a resposta do X (correção de uma auditoria
anterior), em vez de segurar uma única transação durante todo o loop.
Isso tem um efeito colateral positivo para escalabilidade que a análise
confirmou: **nenhuma conexão de banco fica presa durante o
`time.sleep` do Jitter** entre contas — o commit da conta anterior já
liberou a conexão de volta ao pool antes do sleep da próxima começar.
Retries concorrentes do mesmo post (ex.: usuário clica "publicar" duas
vezes) são seguros: a segunda chamada usa `SELECT ... FOR UPDATE SKIP
LOCKED` para pegar as contas ainda pendentes: se a primeira chamada já
está com o lock, a segunda simplesmente não vê nenhuma conta disponível
e retorna `ConflictException` ("Post já está sendo publicado por outra
requisição") em vez de publicar em duplicidade. **Nenhuma mudança
necessária aqui.**

## 2. Banco de dados / pool de conexões — sem gargalo (após a correção do item 3)

`app/database/session.py` usa os padrões do SQLAlchemy
(`pool_pre_ping=True`, sem `pool_size`/`max_overflow` customizados — 5 +
10 = 15 conexões por processo, 2 processos via `--workers 2` no
Uvicorn). Como nenhuma chamada de publicação mantém uma conexão aberta
durante chamadas de rede/Jitter (ver item 1), essa configuração padrão
é suficiente mesmo com múltiplos clientes publicando simultaneamente
para 100 contas cada — **não foi necessário alterar o pool**. A única
fonte real de pressão prolongada sobre uma conexão era o scheduler (ver
item 3), já corrigida.

## 3. Scheduler — gargalo real, corrigido

**O problema:** `app.scheduler.process_due_scheduled_posts` reivindicava
até `SCHEDULER_BATCH_SIZE` (25, padrão) agendamentos vencidos de uma vez
com `SELECT ... FOR UPDATE SKIP LOCKED`, e só commitava (liberando os
locks e a conexão) **depois de publicar todos os 25**, um a um, na MESMA
transação. Publicar um único post com muitas contas já pode levar
bastante tempo (Jitter entre contas + upload de mídia por conta + a
própria chamada à API do X); publicar até 25 posts assim, na mesma
transação, podia manter uma conexão do Postgres presa por um tempo
desproporcional. Como o job roda com `max_instances=1`
(`app.scheduler.start_scheduler`), nenhuma nova execução do mesmo job
começava enquanto a anterior não terminasse — ou seja, **um único
cliente grande (ex.: plano Agência, 100 contas) podia represar TODOS os
agendamentos do sistema, de qualquer outro cliente**, atrás de si.

Matemática ilustrativa (não é um benchmark, apenas ordem de grandeza a
partir dos valores configurados): com o Jitter padrão (1,5–8s, média
~5s) e 100 contas em um único post, só os intervalos entre contas somam
algo da ordem de 99 × 5s ≈ 8 minutos — antes de contar a latência real
de cada chamada ao X. Multiplicado por até 25 posts represados na mesma
transação do lote, o represamento do scheduler inteiro podia chegar
facilmente à casa das horas.

**A correção** (`app/scheduler.py`): reivindicar (e já marcar
`executed=True`/`attempts += 1`) **um agendamento por vez**, cada um em
sua própria transação de milissegundos, liberando o lock e a conexão
imediatamente — a publicação em si acontece depois, em uma sessão
totalmente separada (`_publish_claimed_post`, já existente). O laço
`process_due_scheduled_posts` continua respeitando
`SCHEDULER_BATCH_SIZE` como teto de posts por tick, mas nunca mais
mantém uma transação de reivindicação aberta durante a publicação.

**Trade-off aceito e documentado no código:** marcar `executed=True`
antes de publicar (em vez de só ao final, como antes) significa que, no
caso raro de o processo do worker morrer exatamente durante a
publicação de um post específico, esse agendamento não será
automaticamente re-tentado pelo scheduler (ficará `executed=True`
mesmo que parcialmente publicado). O escopo desse risco agora é **um
post por vez**, não o lote inteiro, e o usuário sempre pode republicar
manualmente via `POST /posts/{id}/publish` (mesmo fluxo idempotente).
O represamento sistêmico do lote inteiro — que acontecia sempre que um
cliente grande tinha um post agendado, não só em crash raro — era o
problema real, e esse é o trade-off certo.

**Validado** com um script descartável: 3 agendamentos vencidos criados
com um `_publish_claimed_post` dublê (nunca toca o X real); confirmado
que os 3 são processados em uma única chamada a
`process_due_scheduled_posts` e que todos ficam `executed=True`/
`attempts=1` ao final.

## 4. Publicação Inteligente / Groq — risco real, corrigido

**O problema:** `AIContentVariationService._request_valid_variations`
pedia **todas as variações de uma vez em uma única chamada à Groq** —
para o plano Agência (100 contas), isso significa pedir 100 variações
de texto distintas em uma única resposta JSON, dentro do orçamento fixo
de `GROQ_TIMEOUT_SECONDS` (15s, independente de quantas variações foram
pedidas). Dois riscos concretos: (1) gerar uma resposta muito grande
pode não caber no timeout, fazendo a criação do post falhar por inteiro
com 5+ contas (regra obrigatória, sem fallback — ver
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`); (2) pedir muitas variações
distintas de um texto curto em uma única chamada tende a degradar a
diversidade real entre elas (o próprio prompt já pede "nunca repita o
mesmo esqueleto de frase" — mais difícil de cumprir para 100 variações
de um só golpe), aumentando a taxa de descarte por duplicidade nas
validações determinísticas já existentes.

**A correção** (`app/services/ai_content_variation_service.py` +
`AI_CONTENT_VARIATION_MAX_BATCH_SIZE`, novo em
`app/config/settings.py`, padrão 20): `_request_valid_variations` agora
divide qualquer pedido maior que o tamanho do lote configurado em
múltiplas chamadas sequenciais menores à Groq, acumulando as variações
válidas até atingir a quantidade necessária (ou esgotar um número
máximo de tentativas, evitando qualquer risco de laço indefinido). Para
o caso comum (até poucas dezenas de contas, o tamanho do lote por
padrão), o comportamento é **idêntico ao anterior**: uma única chamada.
Só quando o número de contas excede o tamanho do lote (ex.: 45, 100) é
que a geração passa a ser feita em partes.

**Validado** com um `GroqClient` dublê: pedido de 45 variações resultou
em 3 chamadas de tamanhos `[20, 20, 5]`, todas as 45 válidas e
distintas; pedido de 4 variações (abaixo do tamanho do lote) continuou
resultando em exatamente 1 chamada, confirmando que o caminho comum não
mudou.

## 5. Chamadas HTTP à API do X — ineficiência real, corrigida

**O problema:** `XOAuthClient` abria um `httpx.Client` novo (`with
httpx.Client(...) as client:`) a cada única chamada — renovação de
token, cada chunk de upload de mídia, e a publicação do tweet em si —
mesmo quando várias dessas chamadas, na mesma execução de
`publish_post`, iam para o mesmo host (`api.x.com`). Para um post com
muitas contas, isso significa abrir e fechar centenas de conexões
TCP/TLS ao mesmo host dentro da mesma chamada, cada handshake sendo
puro overhead de rede sem nenhum benefício — não é uma falha de
correção, mas um desperdício de tempo e recursos que cresce
linearmente com o número de contas.

**A correção** (`app/oauth/oauth_client.py`): `XOAuthClient` passa a
manter um único `httpx.Client` (pool de conexões keep-alive) para toda
a vida da instância, reaproveitado por todas as chamadas. Como cada
`PostService`/`XOAuthClient` já é criado uma vez por requisição/execução
do scheduler (nunca compartilhado entre requisições diferentes — ver
`app/auth/dependencies.py`), isso não introduz nenhum estado
compartilhado indevido entre usuários. `close()` é chamado
explicitamente ao final do único ponto de uso de cada instância
(`PostService.publish_post`, `XOAuthService.complete_callback`),
evitando manter sockets abertos além do necessário.

**Validado**: `python -c "import app.main"` (import limpo), suíte
`pytest` (5 passaram, 1 falha pré-existente e não relacionada),
verificação manual de que `XOAuthClient().close()` funciona
corretamente após uso.

**Nota — `GroqClient` tem o mesmo padrão** (`httpx.Client` novo por
chamada), mas não foi alterado: depois da correção do item 4, uma
única geração de preview faz no máximo ~6–7 chamadas à Groq mesmo para
100 contas (não centenas), então o overhead é limitado e não cresce
proporcionalmente ao número de contas da mesma forma que acontecia no
loop de publicação por conta.

## 6. Upload de mídia (memória) — sem gargalo

`XOAuthClient._media_append` já lê o arquivo em disco em chunks
(`X_MEDIA_UPLOAD_CHUNK_SIZE_BYTES`, 4MB por padrão) via `source.read(chunk_size)`
dentro de um `with file_path.open("rb")`, nunca carregando o arquivo
inteiro em memória. Isso vale para cada conta de destino (o arquivo é
reenviado uma vez por conta, já que cada conta do X tem sua própria
biblioteca de mídia), mas o consumo de memória por chamada é sempre
limitado ao tamanho do chunk, não ao tamanho do arquivo — mesmo para o
limite máximo de 512MB de vídeo e 100 contas de destino. **Nenhuma
mudança necessária.**

## 7. Listagem de contas conectadas — observação, não uma falha

`GET /twitter-accounts` tem `limit` com teto rígido de 100
(`Query(default=100, ge=1, le=100)`), e o maior plano do catálogo
(Agência) permite exatamente 100 contas — os dois valores já batem
exatamente. Não é uma falha para o cenário pedido (até 100 contas), mas
é um teto que merece atenção se o catálogo de planos algum dia
permitir mais de 100 contas: o endpoint precisaria de paginação real no
frontend (`AccountSelector`, `AccountsPage`) para não truncar
silenciosamente a lista. Não alterado nesta análise por estar fora do
escopo pedido (nenhum plano atual excede 100).

## 8. Publicação imediata síncrona — risco residual aceito, não alterado

`POST /posts/{id}/publish` continua sendo uma chamada HTTP síncrona
que, para um post com muitas contas, pode levar de segundos (10 contas)
a vários minutos (100 contas, considerando o Jitter entre cada uma mais
a latência real de cada chamada ao X). Isso é uma consequência direta e
esperada da arquitetura atual (nenhuma rota é `async`, todo o backend é
síncrono por decisão de projeto — ver `claude.md`), não um bug
introduzido por nenhuma funcionalidade recente. Para 100 contas, uma
requisição HTTP tão longa arrisca esbarrar em timeouts de proxy/load
balancer/navegador antes mesmo de o backend terminar — o processamento
no backend continua e termina corretamente (a rota roda em uma thread
do Uvicorn, não é cancelada por um cliente que desistiu), mas o usuário
pode não receber a confirmação na mesma tela.

**Por que não foi alterado nesta tarefa:** eliminar esse risco exigiria
transformar a publicação imediata em um fluxo assíncrono/em segundo
plano (ex.: aceitar o pedido e processar via o mesmo worker do
scheduler, com o frontend consultando o status depois) — uma mudança de
comportamento visível ao usuário (a resposta deixaria de confirmar
"publicado" na hora) e uma decisão de produto, não apenas uma correção
técnica contida. Está fora do escopo desta análise ("não implemente
nenhuma outra funcionalidade"), mas é uma recomendação explícita para
uma decisão futura caso o produto passe a ter clientes reais no plano
Agência publicando rotineiramente para as 100 contas de uma vez.

## Arquivos alterados nesta tarefa

- `backend/app/scheduler.py` — reivindicação um agendamento por vez.
- `backend/app/services/ai_content_variation_service.py` — geração de
  variações em lotes.
- `backend/app/config/settings.py` / `.env.example` / `.env` —
  `AI_CONTENT_VARIATION_MAX_BATCH_SIZE`.
- `backend/app/oauth/oauth_client.py` — `httpx.Client` persistente e
  reaproveitado.
- `backend/app/oauth/oauth_service.py` — fecha o `XOAuthClient` ao
  final do callback OAuth.
- `backend/app/services/post_service.py` — fecha o `XOAuthClient` ao
  final de `publish_post`.

Nenhuma migration foi necessária (nenhuma mudança de schema). Nenhum
comportamento visível ao cliente final mudou — as correções são
inteiramente internas (timing/eficiência/robustez), preservando
exatamente as mesmas regras de negócio, status e respostas de API já
existentes.
