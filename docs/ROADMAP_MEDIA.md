# Suporte a Midia (imagem/gif/video) - Especificacao e estado implementado

Este documento registra a especificacao oficial e o estado JA
IMPLEMENTADO do suporte a midia em publicacoes do XHub, seguindo o
mesmo formato de `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`. Diferente
daquele arquivo (spec para implementacao futura), este documento
descreve uma funcionalidade **completa e validada** nesta base de
codigo -- trate o codigo como fonte da verdade em caso de divergencia
futura, e atualize este arquivo quando o comportamento mudar.

## Objetivo

Permitir que o usuario, no MESMO fluxo de criacao de post (nao uma
tela separada), escreva o texto e anexe imagens/gif/video, com preview
imediato, e publique em uma ou mais contas do X com a midia IDENTICA
em todas as contas -- apenas o texto pode variar (Publicacao
Inteligente, ver `docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`, que
continua atuando exclusivamente sobre o texto e nunca toca em midia).

## Regras de negocio oficiais

- A midia pertence ao `Post`, nao a uma conta especifica: e publicada
  de forma identica (mesmos bytes) em todas as contas de destino.
- Um post pode ter ate 4 arquivos de midia.
- Combinacoes permitidas (mesma regra da API oficial do X):
  - Ate 4 imagens (JPEG/PNG/WEBP) juntas.
  - Exatamente 1 GIF sozinho (nao pode combinar com outra midia).
  - Exatamente 1 video sozinho (nao pode combinar com outra midia).
- Limites de tamanho por tipo: imagem 5MB, GIF 15MB, video 512MB
  (mesmos limites da API oficial do X).
- A midia e enviada e validada ANTES do post existir
  (`POST /media/upload`), com preview imediato no navegador -- a
  confirmacao do post (`POST /posts`) apenas ANEXA a midia ja enviada
  via `media_ids`, na ordem informada.
- Midia nao anexada a nenhum post pode ser removida pelo proprio
  usuario (`DELETE /media/{id}`); midia ja anexada a um post so e
  removida junto com o post (`DELETE /posts/{id}`, que tambem apaga o
  arquivo do disco).
- Funciona identicamente para publicacao imediata E agendada -- o
  agendamento reusa `PostService.publish_post` sem nenhuma logica
  adicional especifica de midia no worker (`app/scheduler.py`).
- A Publicacao Inteligente nunca gera, altera ou remove midia -- atua
  exclusivamente sobre `Post.text`/`PostAccount.rendered_text`.

## Arquitetura implementada

Preserva a arquitetura em camadas do XHub:

```text
Routes -> Services -> Repositories -> Models
```

### Backend

- `app/domain/media_rules.py`
  - Regras puras (sem I/O): tipos de midia aceitos, limites de
    tamanho por tipo, validacao de combinacao (imagens/gif/video).
- `app/core/media_storage.py`
  - Armazenamento em disco (streaming, sem carregar o arquivo inteiro
    em memoria), organizado por usuario. Caminho configuravel via
    `settings.MEDIA_STORAGE_DIR` (padrao `media_storage/`, dentro do
    bind mount `./backend:/app` -- sobrevive a restarts do container
    sem exigir um volume Docker adicional).
- `app/models/post_media.py` (`PostMedia`)
  - `post_id` nullable (midia enviada antes do post existir),
    `user_id` (dono, para autorizacao independente de anexacao),
    `media_type` (enum nativo Postgres), `storage_path`,
    `content_type`, `file_size_bytes`, `position`.
- `app/models/post.py`
  - `Post.media` (`list["PostMedia"]`, `cascade="all, delete-orphan"`,
    ordenado por `position`).
- `app/repositories/post_media_repository.py`
  - `list_by_post`, `list_by_ids_and_user` (valida posse + midia ainda
    nao anexada), `attach_to_post`.
- `app/services/media_service.py` (`MediaService`)
  - `upload_media`: valida `content_type`/tamanho, grava em disco,
    persiste `PostMedia` com `post_id=NULL`.
  - `get_owned_media`/`delete_unattached_media`: autorizacao por dono.
- `app/schemas/media.py`, `app/routes/media.py`
  - `POST /media/upload` (multipart), `GET /media/{id}/file`
    (download/preview autenticado, streaming via `FileResponse`),
    `DELETE /media/{id}` (so midia ainda nao anexada).
- `app/services/post_service.py`
  - `create_post(media_ids=...)`: valida posse + combinacao ANTES de
    criar o `Post`; anexa (`post_id`+`position`) apos a criacao, na
    mesma transacao dos `PostAccount`.
  - `delete_post`: apaga os arquivos do disco ANTES de apagar o `Post`
    (cascade do banco nao sabe tocar o filesystem).
  - `publish_post`: para cada `PostAccount` pendente, envia a midia ao
    X (`XOAuthClient.upload_media`) **uma vez por conta** -- cada
    conta tem seu proprio `access_token`/biblioteca de midia no X, o
    arquivo local e sempre o mesmo -- e so entao publica o tweet com
    `media_ids` (`XOAuthClient.publish_post(media_ids=...)`). Falha no
    upload de midia usa os MESMOS handlers de excecao ja existentes
    (marca o `PostAccount` como `FAILED`, nunca publica sem a midia
    esperada, nunca derruba as demais contas do post).
- `app/oauth/oauth_client.py` (`XOAuthClient`)
  - `upload_media`: protocolo oficial de upload chunked do X, no
    endpoint v2 nativo (`POST https://api.x.com/2/media/upload`,
    comando `INIT`/`APPEND`/`FINALIZE` via campo `command` no mesmo
    endpoint multipart, `STATUS` via query string em um GET) -- chunks
    de `settings.X_MEDIA_UPLOAD_CHUNK_SIZE_BYTES` (padrao 4MB) na
    etapa `APPEND`, polling de `STATUS` ate
    `settings.X_MEDIA_STATUS_MAX_WAIT_SECONDS` apenas quando o X
    retorna `processing_info` (caso assincrono de gif/video).
    Reaproveita `_extract_error_detail` (mesma preservacao do motivo
    original de erro ja usada em `publish_post`). Endpoint e protocolo
    confirmados contra a documentacao oficial atual
    (`docs.x.com/x-api/media`) em 2026-07 -- substitui o endpoint
    legado v1.1 (`upload.twitter.com/1.1/media/upload.json`), que era
    a referencia usada na primeira versao desta implementacao antes da
    verificacao.
  - `publish_post(media_ids=...)`: inclui `{"media": {"media_ids":
    [...]}}` no payload de `POST /2/tweets` quando ha midia.

**Decisao tecnica -- autenticacao do upload de midia:** o endpoint v2
de upload (`api.x.com/2/media/upload`) aceita Bearer OAuth2 de
contexto de usuario (mesmo token OAuth2/PKCE ja usado em todo o resto
do XHub), desde que o escopo `media.write` tenha sido concedido -- por
isso `X_OAUTH_SCOPES` passou a incluir `media.write`. **Contas
conectadas ANTES desta mudanca precisam ser reconectadas** para poder
publicar posts com midia (o escopo e definido no momento da
autorizacao no X, nao pode ser adicionado retroativamente a um token
ja emitido). Nao foi implementada assinatura OAuth 1.0a (consumer
key/secret + HMAC) -- alem de o projeto nunca ter tido essa
infraestrutura, o endpoint v2 atual nem exige mais OAuth 1.0a.

**Decisao tecnica -- deteccao de GIF animado vs. estatico:** nao
adicionada (exigiria uma biblioteca de imagem, ex. Pillow, nao usada
em nenhum outro ponto do projeto). Todo upload com
`content_type=image/gif` e tratado como categoria "gif" (a mais
restritiva das duas), o que e sempre seguro do ponto de vista da API
do X mesmo para um GIF estatico.

**Decisao tecnica -- dimensoes/duracao de midia:** nao persistidas
(exigiria Pillow para imagem ou ffprobe para video, nenhum presente no
projeto). O preview no frontend usa `URL.createObjectURL` sobre o
arquivo local selecionado -- nao depende dessas informacoes.

### Frontend

- `types/media.ts`, `services/media.ts`, `hooks/useMediaUpload.ts`
  - Tipos, chamadas HTTP (`multipart/form-data` no upload) e mutations
    cruas de upload/remocao.
- `hooks/useMediaComposer.ts`
  - Estado do compositor: cada arquivo selecionado ganha preview
    LOCAL instantaneo (`URL.createObjectURL`, sem round-trip ao
    backend) enquanto o upload real roda em paralelo; valida tipo,
    tamanho e combinacao no cliente (mesmas regras de
    `app/domain/media_rules.py`, espelhadas em `lib/mediaRules.ts`)
    antes de tentar o upload, para feedback instantaneo -- o backend
    continua sendo a unica fonte de verdade (revalida tudo de novo).
- `components/posts/MediaComposer.tsx`
  - Botoes de anexar imagem/gif e video logo abaixo do textarea (mesma
    tela, sem tela separada) + grade de preview com remocao, no
    espirito do compositor do X.
- `pages/NewPostPage.tsx`
  - `media_ids` (apenas midias com upload concluido) e enviado junto
    da confirmacao do post (`POST /posts`); o botao de gerar
    Publicacao Inteligente fica desabilitado enquanto houver upload em
    andamento ou com erro.
- `components/intelligent-publication/IntelligentPublicationPreviewModal.tsx`
  - Nota explicita quando ha midia anexada: "sera publicada
    exatamente igual em todas as contas -- a Publicacao Inteligente
    varia apenas o texto".

### Edicao de midia (crop/zoom/rotacao de imagem, corte real de video)

Adicionado a pedido explicito do usuario apos o preview inicial se
mostrar insuficiente para publicacoes que dependem de qualidade de
midia (propagandas, videos de clientes). Decisao explicita do usuario:
TUDO roda no navegador, sem processamento novo no backend.

- `lib/imageCrop.ts` + `components/posts/ImageEditorDialog.tsx`: crop
  (arrastavel/redimensionavel), zoom e rotacao via canvas, usando
  `react-easy-crop`. So para imagens estaticas -- nunca para GIF
  (canvas destruiria a animacao).
- `hooks/useFfmpeg.ts` + `components/posts/VideoTrimmerDialog.tsx`:
  corte real de video (`-c copy`, sem recodificar) via `ffmpeg.wasm`,
  100% client-side. O core (`ffmpeg-core.js`/`.wasm`, ~30MB) e
  self-hosted em `public/ffmpeg/` (`scripts/copy-ffmpeg-core.mjs`,
  rodado no `postinstall`) -- nunca um CDN de terceiros.
- `components/posts/MediaLightbox.tsx`: visualizador em tela cheia
  (zoom/pan em imagem, player nativo completo para video, navegacao
  entre midias do mesmo post).
- `hooks/useMediaComposer.ts`: cada item guarda `originalFile`
  (nunca sobrescrito) -- reeditar sempre parte do arquivo original,
  evitando degradar qualidade a cada edicao sucessiva.

**Nao validado interativamente** (sem navegador automatizado
disponivel no ambiente de desenvolvimento) -- apenas validacao
estatica (tipos, build, assets servidos). Recomenda-se teste manual
completo (crop de imagem, corte de video, navegacao no lightbox) antes
de depender disso em producao com clientes reais.

## Contas conectadas -- foto de perfil real e @username como identificador principal

- `TwitterAccount.profile_image_url` (nova coluna, nullable -- NULL
  para contas conectadas antes desta migration, ate reconexao).
- `XOAuthClient.get_authenticated_user` passa a pedir
  `user.fields=profile_image_url` a API do X e a upgradar a resolucao
  da foto (sufixo `_normal` -> `_400x400`, mesma URL/CDN, sem chamada
  extra).
- Frontend (`TwitterAccountCard.tsx`, `AccountSelector.tsx`): usa
  `AvatarImage` com `profile_image_url` (fallback automatico para as
  iniciais via `AvatarFallback` quando `null`), e passa a exibir
  `@username` como identificador PRINCIPAL (texto em destaque) com
  `display_name` como informacao secundaria (texto mais claro) --
  antes era o oposto.

## Validacao realizada

- `alembic upgrade head`: migrations de `post_media` e
  `twitter_accounts.profile_image_url` aplicadas sem erro; schema
  conferido via `\d post_media` no Postgres.
- `python -c "import app.main"`: aplicacao importa sem erro apos todas
  as mudancas (rotas, dependencias, models).
- Suite `pytest`: 5 passaram, 1 falha PRE-EXISTENTE e nao relacionada
  (`test_get_subscription_returns_subscription_for_admin`, dublê de
  teste desatualizado em relacao a uma mudanca anterior de
  `SubscriptionService.to_domain_context` -- nao introduzida por esta
  tarefa).
- Integracao ponta a ponta via `curl` contra a API real: upload de
  imagem, download autenticado (bytes identicos ao arquivo original),
  bloqueio de acesso sem token (401) e de outro usuario (404, sem
  revelar existencia), remocao com limpeza do arquivo em disco.
- Integracao ponta a ponta via script Python dentro do container
  (removido apos a validacao): `create_post(media_ids=...)` anexa a
  midia com a posicao correta; `publish_post` chama
  `XOAuthClient.upload_media` uma vez por conta ANTES de
  `publish_post(media_ids=...)`, com `media_category`/`content_type`
  corretos (testado com um `XOAuthClient` dublê, sem tocar a API real
  do X); `delete_post` remove o arquivo do disco.
- Frontend: `tsc --noEmit` e `npm run build` (`tsc -b && vite build`)
  limpos, sem erros de tipo; servidor de desenvolvimento verificado via
  `curl` apos restart do container (padrao ja usado neste projeto,
  pois o watcher do Vite nem sempre propaga mudancas de bind mount
  automaticamente neste ambiente).
- **Testado contra a API real do X com a conta do usuario reconectada**
  (2026-07-16, com autorizacao explicita do usuario para o teste):
  - 1ª tentativa (endpoint base `POST /2/media/upload` com campo
    `command=INIT`, herdado do padrao v1.1): `400 Invalid Request:
    Missing media field in JSON`. Diagnostico revelou que o endpoint
    v2 nao usa mais um unico endpoint com `command` -- usa caminhos
    dedicados por etapa.
  - 2ª tentativa, apos reescrever para os caminhos corretos
    (`POST /2/media/upload/initialize` com corpo JSON,
    `POST /2/media/upload/{id}/append` multipart,
    `POST /2/media/upload/{id}/finalize` sem corpo): **INIT e APPEND
    concluidos com sucesso** (200, `media_id` real retornado pelo X).
    FINALIZE retornou `402 Payment Required: credits depleted` -- uma
    falha de billing da conta do X do usuario (sem creditos
    adicionados na API), nao um bug de implementacao. Confirma que a
    autenticacao (Bearer OAuth2 user-context + escopo `media.write`) e
    o protocolo INIT/APPEND estao corretos.
  - `GET /2/media/upload/{id}/status` (usado so no caso assincrono de
    gif/video) segue o mesmo padrao de caminho confirmado para as
    demais etapas, mas NAO foi validado contra a API real (nenhuma
    midia chegou a ser finalizada com sucesso nesta sessao, por causa
    dos creditos) -- validar na primeira publicacao real de um
    gif/video.
  - FINALIZE completo (apos creditos serem adicionados na conta do X)
    e a publicacao efetiva do tweet com midia continuam nao validados
    end-to-end nesta sessao.

## Fora de escopo desta implementacao

- Jitter entre publicacoes (proxima etapa do roadmap do produto, fora
  desta tarefa por instrucao explicita).
- Deteccao de GIF animado vs. estatico, extracao de dimensoes/duracao
  de midia (ver decisoes tecnicas acima).
- Assinatura OAuth 1.0a para upload de midia (ver decisao tecnica
  acima -- Bearer OAuth2 de contexto de usuario usado em seu lugar).
