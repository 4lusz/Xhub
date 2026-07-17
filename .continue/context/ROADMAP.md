# XHub - Roadmap permanente para IA

Este arquivo deve ser mantido como contexto vivo para Continue.dev.

## Atualizacao de 2026-07-16

Desde a ultima revisao deste arquivo (2026-07-09), quatro funcionalidades
saíram do estado "planejado/especificado" para "implementado e validado":
**Publicacao Inteligente** (integracao com Groq), **Midia** (upload +
edicao client-side de imagem/gif/video), **Primeiro Acesso Obrigatorio**
(troca de senha temporaria) e **Jitter** (atraso natural entre
publicacoes). Cada uma tem sua propria especificacao + estado implementado
em `docs/ROADMAP_*.md`. Este arquivo resume o estado consolidado; para
detalhe tecnico completo, ver `claude.md` (raiz do repositorio).

## Estado do roadmap fornecido (historico)

O roadmap oficial da funcionalidade Publicacao Inteligente foi fornecido pelo
usuario e incorporado oficialmente a esta base permanente de conhecimento.
Reproduzido abaixo por valor historico -- **todas as regras descritas foram
implementadas e validadas** (ver `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`
para o detalhe arquivo a arquivo):

```text
Roadmap - Publicacao Inteligente (XHub)

Objetivo
Implementar uma camada de Publicacao Inteligente que gere variacoes naturais
entre publicacoes, preservando o significado original e reduzindo conteudo
repetitivo.

Atencao
Publicar exatamente o mesmo texto em mais de uma conta aumenta
consideravelmente o risco de bloqueios ou limitacoes automaticas pela
plataforma X. A Publicacao Inteligente existe para reduzir esse padrao
repetitivo, preservando o conteudo original.

Regras de Negocio
- 1 conta: publicar texto original.
- 2 a 4 contas: publicar texto original.
- 5 contas ou mais: geracao de variacoes obrigatoria.

Backend
- Utilizar a API da Groq (nao OpenAI).
- Criar AIContentVariationService.
- Cada PostAccount possuir rendered_text proprio.
- Manter sempre o texto original em Post.
- Registrar modelo, tempo, tokens, custo (quando aplicavel) e versao do prompt.
- Implementar cache.
- Tratar indisponibilidade da Groq.

Prompt da IA
Reescrever preservando exatamente o significado. Manter hashtags, @mencoes,
emojis e CTA. Links e URLs sao constantes imutaveis. Nunca expandir, resumir,
reescrever, trocar parametros, alterar dominios, modificar encurtadores
(bit.ly, shopee, etc.) ou qualquer parte da URL. O link deve ser preservado
exatamente como enviado pelo usuario.

Frontend
- Botao 'Publicacao Inteligente'.
- Ate 4 contas: opcional e ativado por padrao.
- Exibir aviso recomendando a funcionalidade para diversificar
  automaticamente as publicacoes.
- Com 5+ contas: obrigatorio.
- Modal de pre-visualizacao.
- Permitir edicao manual das versoes.

Regra para indisponibilidade da Groq
Se houver 5 ou mais contas e a Groq estiver indisponivel, o backend NAO deve
publicar automaticamente o mesmo texto em todas as contas. A publicacao deve
ser interrompida antes do envio ao X e o usuario deve ser informado do motivo,
podendo:
1. tentar novamente;
2. salvar como rascunho;
3. reagendar a publicacao.

Nunca fazer fallback automatico para publicar o mesmo texto em multiplas
contas.
```

Depois desse roadmap, dois outros foram fornecidos e ja implementados:
Primeiro Acesso Obrigatorio (troca de senha temporaria antes de qualquer
rota protegida) e Jitter (atraso natural entre publicacoes em multiplas
contas, configuravel pelo admin).

## Implementado conforme codigo atual

- Backend FastAPI com arquitetura em camadas.
- PostgreSQL com SQLAlchemy 2.0 e Alembic.
- Autenticacao JWT + refresh token opaco com rotacao.
- Primeiro acesso obrigatorio (`must_change_password`, HTTP 428).
- Roles `client` e `admin`; contas admin sem assinatura por design.
- Criacao administrativa de usuarios com assinatura explicita.
- Planos e assinaturas; controle de limite de contas conectadas e saldo de
  posts; posts extras.
- Auditoria administrativa (append-only).
- OAuth2 do X com PKCE; sessao OAuth persistida no Postgres.
- Criptografia de tokens OAuth em repouso (Fernet).
- Conexao, listagem e desconexao de contas do X (com foto de perfil).
- Criacao, agendamento e publicacao de posts em multiplas contas.
- Idempotencia por `PostAccount`.
- Upload e anexacao de midia (imagem/gif/video) a posts, com edicao
  client-side (crop/zoom/rotacao de imagem, corte de video via ffmpeg.wasm).
- **Publicacao Inteligente completa**: `AIContentVariationService`,
  `GroqClient`, `PostAccount.rendered_text`, obrigatoriedade para 5+ contas,
  cache em memoria, modal de pre-visualizacao e edicao manual no frontend,
  tratamento de indisponibilidade da Groq conforme regra oficial.
- **Jitter completo**: atraso aleatorio entre publicacoes em contas
  diferentes, configuravel pelo admin (`min_seconds`/`max_seconds`),
  aplicado apenas a partir da segunda conta de cada chamada de publicacao.
- Scheduler in-process (APScheduler) com `FOR UPDATE SKIP LOCKED`, seguro
  para multiplas replicas do backend.
- Health check de API e banco.
- Frontend completo para cliente (dashboard, contas, posts, agendamento,
  perfil, configuracoes) e para admin (usuarios, planos, assinaturas,
  publicacoes, auditoria, Jitter, estatisticas), com roteamento e navegacao
  segregados por papel.

## Planejado / nao implementado (genuino, nao coberto por nenhum docs/ROADMAP_*.md)

- Registro de custo monetario por chamada a Groq (a API usada nao expoe
  custo diretamente; apenas tokens/latencia/modelo sao registrados hoje).
- Cache de variacoes de IA persistido em banco (hoje e em memoria, por
  processo -- decisao tecnica aceita, nao uma lacuna urgente).
- `PublicationContentType`/custo de publicacao por tipo de conteudo
  (`app/domain/publication_cost.py` existe mas nao esta conectado ao fluxo
  real de publicacao).
- Auditoria de conexao/desconexao de conta do X e de criacao de assinatura
  (`AuditAction.TWITTER_ACCOUNT_CONNECTED`/`TWITTER_ACCOUNT_DISCONNECTED`/
  `SUBSCRIPTION_CREATED` existem no enum mas nunca sao de fato registrados).
- Testes automatizados para `publish_post`, `AIContentVariationService`,
  `JitterService`, scheduler e funcoes puras de `app.domain` (validacao hoje
  e manual, documentada em `docs/ROADMAP_*.md` a cada feature).
- Autoatendimento de "esqueci minha senha" pelo cliente (fluxo de e-mail) --
  fora de escopo por decisao explicita; hoje so existe redefinicao
  administrativa.

## Decisoes tecnicas oficiais (Publicacao Inteligente, ja implementadas)

- A funcionalidade preserva a arquitetura em camadas do XHub.
- Usa Groq, nunca OpenAI.
- `Post.text` guarda sempre o texto original.
- Cada `PostAccount` possui seu proprio `rendered_text`.
- Para 1 conta, publica texto original (Groq nunca chamada).
- Para 2 a 4 contas, variacao opcional e ativada por padrao no frontend, com
  aviso recomendando diversificacao automatica.
- Para 5 contas ou mais, geracao de variacoes obrigatoria, sem fallback para
  texto igual.
- Com 5+ contas, se a Groq estiver indisponivel, a publicacao e interrompida
  antes de qualquer chamada ao X.
- O prompt preserva exatamente significado, hashtags, @mencoes, emojis e CTA;
  URLs sao imutaveis (nunca expandidas, resumidas, reescritas ou com
  parametros/dominio/encurtador alterados) -- qualquer variacao que viole
  isso e descartada deterministicamente, nunca corrigida por tentativa.

## Divergencias conhecidas (atuais, nao historicas)

- `app.domain.enums` duplica `UserRole`/`SubscriptionStatus` de
  `app.models.enums` -- sincronizacao manual, dívida tecnica aceita.
- Schemas de `Post`/`ScheduledPost` ainda vivem dentro de
  `app/routes/post.py`, nao em `app.schemas` (padrao usado por features mais
  novas, como Publicacao Inteligente e Midia).
- Suite `pytest` fina; uma falha pre-existente e nao relacionada
  (`test_get_subscription_returns_subscription_for_admin`) estavel ha varias
  features.

Lista completa e atualizada de divergencias/dividas tecnicas: ver secao
"Lacunas e dividas tecnicas conhecidas" em `claude.md`.
