# Publicacao Inteligente - Especificacao oficial para implementacao futura

Este documento e a especificacao tecnica oficial para uma IA ou desenvolvedor
implementar a funcionalidade Publicacao Inteligente no XHub. Ele incorpora o
roadmap oficial fornecido pelo usuario e deve ser seguido preservando a
arquitetura atual do XHub e evitando refatoracoes desnecessarias.

Nao ha logica de negocio implementada nesta tarefa; este arquivo define a
arquitetura, regras e roadmap esperados.

## Objetivo

Implementar uma camada de Publicacao Inteligente que gere variacoes naturais
entre publicacoes, preservando o significado original e reduzindo conteudo
repetitivo.

Permitir que o usuario escreva um texto original uma unica vez e publique em
uma ou mais contas do X com controle de variacoes por conta, preservando o
texto original e armazenando a versao final usada em cada conta quando a
funcionalidade exigir ou gerar variacoes.

## Atencao

Publicar exatamente o mesmo texto em mais de uma conta aumenta
consideravelmente o risco de bloqueios ou limitacoes automaticas pela
plataforma X.

A Publicacao Inteligente existe para reduzir esse padrao repetitivo,
preservando o conteudo original.

## Estado atual relevante

O fluxo atual cria um `Post` com `Post.text` e um `PostAccount` para cada conta
selecionada. A publicacao usa `Post.text` diretamente para todas as contas.

Limitacoes atuais:

- `PostAccount` nao possui `rendered_text`.
- Nao existe cliente Groq.
- Nao existe `AIContentVariationService`.
- Nao existe service de geracao de variacoes.
- Nao existe endpoint de preview.
- Nao existe frontend de modal/edicao de variacoes.
- Nao existe botao "Publicacao Inteligente".
- Nao existe regra de obrigatoriedade para 5+ contas.
- Nao existe cache de variacoes de IA.
- Nao existe registro estruturado de modelo, tempo, tokens, custo e versao do
  prompt para esta funcionalidade.

## Principio central

`Post.text` deve continuar sendo sempre o texto original escrito pelo usuario.
`PostAccount.rendered_text` deve ser o texto efetivamente publicado em cada
conta quando houver variacao, edicao manual ou materializacao do texto final
por conta.

Nunca sobrescrever `Post.text` com conteudo gerado por IA.

Cada `PostAccount` deve possuir `rendered_text` proprio.

## Regras de negocio oficiais

- 1 conta: publicar texto original.
- 2 a 4 contas: publicar texto original.
- 5 contas ou mais: geracao de variacoes obrigatoria.
- Com 5+ contas, a publicacao nao pode seguir para o X sem variacoes validas.
- O usuario deve revisar as variacoes antes da publicacao quando houver
  geracao.
- O usuario pode editar manualmente qualquer versao gerada.
- Publicacao deve continuar idempotente: `PostAccount` ja `PUBLISHED` nao pode
  ser alterado ou republicado em retry.
- Falha parcial em uma conta deve continuar isolada em `PostAccount`.
- A assinatura e o saldo devem continuar sendo validados antes de qualquer
  efeito externo irreversivel no X.
- Publicar o mesmo texto em multiplas contas quando ha 5+ contas selecionadas
  e uma violacao da especificacao oficial, salvo se uma futura decisao tecnica
  documentada alterar essa regra.

## Regras por quantidade de contas

### 1 conta

- Publicar texto original.
- Nao chamar Groq por obrigatoriedade.
- `rendered_text` pode ser igual ao texto original se a implementacao decidir
  materializar o texto final por conta.

### 2 a 4 contas

- Publicar texto original como regra de negocio oficial.
- No frontend, a funcionalidade Publicacao Inteligente deve ser opcional e
  ativada por padrao.
- O frontend deve exibir aviso recomendando a funcionalidade para diversificar
  automaticamente as publicacoes.
- Se o usuario mantiver a funcionalidade ativada e a implementacao suportar
  variacoes opcionais, o fluxo deve continuar exigindo pre-visualizacao e
  aprovacao antes da publicacao.
- Se o usuario desativar ou nao confirmar variacoes opcionais, o backend pode
  publicar o texto original.

### 5 contas ou mais

- Geracao de variacoes obrigatoria.
- A Groq deve estar disponivel ou deve haver cache valido previamente gerado
  para o mesmo contexto.
- Nao publicar automaticamente o mesmo texto em todas as contas.
- Se a Groq estiver indisponivel e nao houver variacoes validas, interromper a
  publicacao antes do envio ao X.
- Informar o usuario do motivo.
- Permitir ao usuario:
  1. tentar novamente;
  2. salvar como rascunho;
  3. reagendar a publicacao.
- Nunca fazer fallback automatico para publicar o mesmo texto em multiplas
  contas.

## Backend

Requisitos oficiais:

- Utilizar a API da Groq.
- Nao utilizar OpenAI para esta funcionalidade.
- Criar `AIContentVariationService`.
- Cada `PostAccount` deve possuir `rendered_text` proprio.
- Manter sempre o texto original em `Post`.
- Registrar modelo, tempo, tokens, custo quando aplicavel e versao do prompt.
- Implementar cache.
- Tratar indisponibilidade da Groq.

## Prompt da IA

O prompt da IA deve seguir estas regras:

- Reescrever preservando exatamente o significado.
- Manter hashtags.
- Manter @mencoes.
- Manter emojis.
- Manter CTA.
- Links e URLs sao constantes imutaveis.
- Nunca expandir URLs.
- Nunca resumir URLs.
- Nunca reescrever URLs.
- Nunca trocar parametros de URLs.
- Nunca alterar dominios.
- Nunca modificar encurtadores, incluindo `bit.ly`, `shopee` e similares.
- Nunca modificar qualquer parte da URL.
- O link deve ser preservado exatamente como enviado pelo usuario.

Estas regras devem ser reforcadas no service antes e depois da chamada a IA.
Mesmo que a Groq retorne uma variacao que altere URL, parametros, dominio,
encurtador, hashtag, @mencao, emoji ou CTA, a resposta deve ser considerada
invalida ou corrigida por uma estrategia deterministica documentada.

## Frontend

Requisitos oficiais:

- Botao "Publicacao Inteligente".
- Ate 4 contas: opcional e ativado por padrao.
- Exibir aviso recomendando a funcionalidade para diversificar
  automaticamente as publicacoes.
- Com 5+ contas: obrigatorio.
- Modal de pre-visualizacao.
- Permitir edicao manual das versoes.

## Regra para indisponibilidade da Groq

Se houver 5 ou mais contas e a Groq estiver indisponivel, o backend NAO deve
publicar automaticamente o mesmo texto em todas as contas.

A publicacao deve ser interrompida antes do envio ao X e o usuario deve ser
informado do motivo, podendo:

1. tentar novamente;
2. salvar como rascunho;
3. reagendar a publicacao.

Nunca fazer fallback automatico para publicar o mesmo texto em multiplas
contas.

## Fluxo completo proposto

1. Usuario escreve `text` original e seleciona contas.
2. Frontend mostra o botao "Publicacao Inteligente".
3. Frontend avalia quantidade de contas:
   - 1 conta: publicar texto original.
   - 2 a 4 contas: funcionalidade opcional e ativada por padrao; exibir aviso
     recomendando diversificacao automatica.
   - 5+ contas: funcionalidade obrigatoria.
4. Frontend solicita preview inteligente quando a funcionalidade estiver ativa
   ou obrigatoria.
5. Backend valida usuario, contas e posse.
6. Backend decide estrategia pela quantidade de contas.
7. Backend consulta cache de variacoes, se aplicavel.
8. Backend chama Groq quando necessario.
9. Backend valida que as variacoes preservam significado e elementos
   imutaveis.
10. Backend retorna preview com uma versao por conta.
11. Frontend exibe modal de pre-visualizacao.
12. Usuario edita manualmente variacoes se desejar.
13. Frontend envia criacao/confirmacao do post com textos finais.
14. Backend cria `Post` com texto original.
15. Backend cria `PostAccount` por conta com `rendered_text` proprio quando
    houver texto final por conta.
16. Publicacao usa `PostAccount.rendered_text` quando existir; fallback para
    `Post.text` somente para compatibilidade com registros antigos e cenarios
    onde a regra permite texto original.
17. `PostService.publish_post` mantem validacoes comerciais antes de chamar X.
18. Em 5+ contas, se nao houver variacoes validas, a publicacao e interrompida
    antes de qualquer chamada para o X.

## Arquitetura da solucao

Preservar arquitetura atual:

```text
Routes -> Services -> Repositories -> Models
```

Adicionar integracao Groq como cliente isolado, sem acoplar HTTP externo nas
rotas.

Service principal:

- `AIContentVariationService`

Responsabilidades do `AIContentVariationService`:

- Receber texto original e contas de destino.
- Determinar se a geracao e opcional, desnecessaria ou obrigatoria.
- Orquestrar cache.
- Chamar cliente Groq quando necessario.
- Validar variacoes retornadas.
- Garantir preservacao exata de URLs, hashtags, @mencoes, emojis e CTA.
- Medir e registrar modelo, tempo, tokens, custo quando aplicavel e versao do
  prompt.
- Retornar preview seguro para a rota/frontend.
- Tratar indisponibilidade da Groq de acordo com a regra oficial.

## Arquivos previstos para implementacao futura

Backend:

- `backend/app/integrations/groq_client.py`
  - Cliente HTTP da Groq.
  - Responsavel por timeout, payload, parse de resposta e erros de integracao.
  - Nao deve conhecer models SQLAlchemy.
  - Deve expor metadados de modelo, tokens e custo quando a API fornecer.

- `backend/app/services/ai_content_variation_service.py`
  - Nome oficial do service: `AIContentVariationService`.
  - Orquestra geracao de variacoes.
  - Recebe cliente Groq e repositories necessarios.
  - Decide estrategia por quantidade de contas.
  - Aplica cache.
  - Valida preservacao de significado e elementos imutaveis.
  - Retorna objetos de preview sem publicar no X.
  - Interrompe fluxo obrigatorio quando Groq estiver indisponivel.

- `backend/app/schemas/intelligent_publication.py`
  - Schemas Pydantic de request/response.
  - Deve incluir texto original, contas selecionadas, previews por conta,
    textos editados e flags de obrigatoriedade/opcionalidade.

- `backend/app/routes/intelligent_publication.py`
  - Endpoints de preview/confirmacao, se a implementacao separar do fluxo atual.
  - Deve depender de `get_current_user`, service e `get_db`.
  - Nao deve conter regra de negocio de geracao.

- `backend/app/repositories/intelligent_publication_cache_repository.py`
  - Somente se o cache for persistido em banco.
  - Encapsula busca/criacao/invalidacao de cache.

- `backend/app/models/intelligent_publication_cache.py`
  - Somente se o cache persistente for adotado.
  - Deve conter hash do texto original, ids/assinatura das contas, versoes
    geradas, metadata de modelo, tempo, tokens, custo quando aplicavel, versao
    do prompt e expiracao.

- `backend/alembic/versions/*_add_rendered_text_to_post_accounts.py`
  - Migration obrigatoria para `PostAccount.rendered_text`.

- `backend/alembic/versions/*_create_intelligent_publication_cache.py`
  - Migration somente se cache persistente for implementado.

Alteracoes futuras em arquivos existentes:

- `backend/app/models/post_account.py`
  - Adicionar `rendered_text: Mapped[str | None] = mapped_column(Text, nullable=True)`.

- `backend/app/services/post_service.py`
  - Em `publish_post`, usar `post_account.rendered_text or post.text`.
  - Nao alterar idempotencia.
  - Garantir que 5+ contas nao sejam publicadas sem variacoes validas quando a
    regra obrigatoria se aplicar.

- `backend/app/auth/dependencies.py`
  - Adicionar factory para `AIContentVariationService`.

- `backend/app/main.py`
  - Registrar router de Publicacao Inteligente, se houver rota nova.

- `backend/app/config/settings.py`
  - Adicionar `GROQ_API_KEY`, modelo, timeout, versao do prompt e flags de
    cache.

- `backend/app/models/__init__.py`
  - Exportar novos models, se cache persistente for criado.

Frontend:

- `frontend/src/services/intelligentPublication.ts`
  - Chamadas ao backend para preview/confirmacao.

- `frontend/src/types/intelligentPublication.ts`
  - Tipos de preview, variacoes por conta, request de confirmacao, estado de
    obrigatoriedade e metadados exibiveis.

- `frontend/src/components/IntelligentPublicationPreviewModal.tsx`
  - Modal de revisao e edicao manual.

- `frontend/src/hooks/useIntelligentPublication.ts`
  - Query/mutation para gerar preview e confirmar.

- Componente ou ajuste na tela de criacao de post:
  - Botao "Publicacao Inteligente".
  - Estado ativado por padrao ate 4 contas.
  - Estado obrigatorio com 5+ contas.
  - Aviso recomendando diversificacao automatica.

## Fluxo Routes -> Services -> Repositories

Preview:

```text
route preview
-> valida usuario autenticado
-> AIContentVariationService.generate_preview
-> TwitterAccountRepository valida contas e posse
-> AIContentVariationService decide regra por quantidade de contas
-> cache repository busca variacao existente, se aplicavel
-> GroqClient gera faltantes, se necessario
-> AIContentVariationService valida resposta
-> cache repository salva resultado, se aplicavel
-> response com preview por conta
```

Confirmacao:

```text
route create/confirm
-> valida usuario autenticado
-> valida textos finais e obrigatoriedade
-> PostService.create_post ou metodo especifico
-> PostRepository cria Post com texto original
-> PostAccountRepository cria PostAccount por conta com rendered_text
-> commit unico
```

Publicacao:

```text
route publish
-> PostService.publish_post
-> valida posse, assinatura e saldo
-> valida regra obrigatoria de 5+ contas antes do envio ao X
-> para cada PostAccount pendente/falha
-> XOAuthClient.publish_post(text=post_account.rendered_text or post.text)
-> marca status por conta
```

## Integracao prevista com Groq

Configuracoes futuras:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_TIMEOUT_SECONDS`
- `AI_CONTENT_VARIATION_PROMPT_VERSION`
- `INTELLIGENT_PUBLICATION_CACHE_ENABLED`
- `INTELLIGENT_PUBLICATION_CACHE_TTL_SECONDS`

Regras:

- Chamar Groq apenas dentro de cliente dedicado.
- Nunca registrar API key em logs.
- Timeout deve ser curto e configuravel.
- Erros 401/403 indicam configuracao invalida.
- Erros 429 devem ser tratados como limite temporario.
- Erros 5xx devem ser tratados como indisponibilidade temporaria.
- Resposta deve ser validada antes de retornar ao usuario.
- Registrar modelo, tempo, tokens, custo quando aplicavel e versao do prompt.
- Nao usar OpenAI para esta funcionalidade.

## Estrategia de geracao de variacoes

Para 1 conta:

- Publicar texto original.
- Nao chamar Groq por obrigatoriedade.

Para 2 a 4 contas:

- Publicar texto original como regra oficial.
- A Publicacao Inteligente e opcional no frontend e ativada por padrao.
- Exibir aviso recomendando diversificacao automatica.
- Se o usuario confirmar geracao opcional, aplicar o mesmo rigor de
  preservacao de significado, URLs, hashtags, @mencoes, emojis e CTA.

Para 5 ou mais contas:

- Geracao de variacoes obrigatoria.
- Gerar em lote ou por grupos, conforme implementacao.
- Exigir diversidade suficiente para reduzir repeticao.
- Validar duplicatas antes de responder.
- Se a Groq retornar menos variacoes que o necessario, nao publicar
  automaticamente o mesmo texto para as contas faltantes.
- Se nao houver variacoes validas para todas as contas exigidas, retornar erro
  recuperavel e permitir tentar novamente, salvar rascunho ou reagendar.

## Uso de rendered_text em PostAccount

`PostAccount.rendered_text` deve guardar exatamente o texto aprovado para a
conta correspondente.

Regras:

- Cada `PostAccount` possui `rendered_text` proprio.
- Pode ser `NULL` para posts antigos.
- Para novos posts com preview inteligente, deve ser preenchido quando houver
  variacao ou edicao manual.
- Para 5+ contas, deve haver texto final valido por conta antes da publicacao.
- Publicacao deve usar fallback `post.text` quando `rendered_text` estiver
  ausente somente para compatibilidade retroativa e para cenarios em que o
  texto original e permitido pela regra de negocio.
- Editar manualmente uma versao antes de publicar deve atualizar somente
  `rendered_text` daquela conta.

## Preservacao do texto original

- `Post.text` e imutavel como fonte original apos criacao, salvo se uma futura
  feature explicita de edicao de rascunho for especificada.
- Variacoes nunca devem substituir `Post.text`.
- Logs e auditoria devem conseguir distinguir texto original e texto renderizado
  sem expor conteudo sensivel desnecessariamente.
- Manter sempre o texto original em `Post`.

## Cache

Cache recomendado para preview:

- Chave: hash de `original_text`, ids das contas selecionadas, modelo Groq e
  versao do prompt.
- Considerar tambem versao da estrategia de geracao.
- TTL curto, configuravel.
- Cache nao deve ser usado apos edicao manual.
- Cache nao deve conter segredo.
- Se armazenar textos gerados, tratar como dado do usuario.
- Invalidar quando mudar modelo, prompt, estrategia ou conjunto de contas.
- Cache valido pode permitir continuar fluxo de 5+ contas mesmo se Groq estiver
  indisponivel, desde que as variacoes tenham sido geradas anteriormente para o
  mesmo contexto e ainda sejam validas.

## Logs e metricas

Registrar:

- Inicio/fim da geracao de preview.
- Quantidade de contas.
- Estrategia escolhida.
- Obrigatoriedade ou opcionalidade da geracao.
- Uso de cache hit/miss.
- Modelo Groq usado.
- Tempo de resposta.
- Tokens usados.
- Custo quando aplicavel.
- Versao do prompt.
- Erros de Groq com tipo/status, sem prompt completo e sem API key.
- Confirmacao de textos finais sem logar conteudo integral por padrao.
- Interrupcao de publicacao por indisponibilidade da Groq em fluxo de 5+ contas.

Nao registrar:

- API keys.
- Access tokens/refresh tokens.
- Prompt completo se contiver texto do usuario.
- Resposta integral da IA em logs de producao.
- URLs sensiveis alem do necessario para diagnostico seguro.

## Tratamento de falhas da Groq

- Falha na Groq durante preview nao deve criar post nem `PostAccount`, salvo se
  o fluxo escolhido for explicitamente salvar rascunho sem publicar.
- Retornar erro claro para o frontend.
- Permitir retry.
- Para 1 conta, publicar texto original e possivel sem Groq.
- Para 2 a 4 contas, publicar texto original e permitido pela regra oficial se
  a variacao opcional nao puder ser gerada ou nao for confirmada.
- Para 5+ contas, nao publicar automaticamente fallback duplicado.
- Para 5+ contas, interromper antes do envio ao X quando a Groq estiver
  indisponivel e nao houver cache valido.
- Para 5+ contas, informar o usuario e permitir tentar novamente, salvar como
  rascunho ou reagendar.
- Em 429/5xx, indicar indisponibilidade temporaria.
- Em resposta invalida, tratar como erro de integracao.
- Nunca fazer fallback automatico para publicar o mesmo texto em multiplas
  contas.

## Modal de pre-visualizacao

O modal deve:

- Mostrar texto original.
- Mostrar uma linha/card por conta selecionada.
- Exibir username/display name da conta.
- Permitir edicao manual do texto por conta.
- Validar limite de caracteres por conta.
- Destacar textos duplicados ou vazios.
- Bloquear confirmacao se qualquer texto estiver invalido.
- Confirmar explicitamente antes de publicar ou salvar.
- Indicar quando a Publicacao Inteligente e obrigatoria por haver 5+ contas.
- Indicar quando a Publicacao Inteligente e opcional para ate 4 contas.

## Edicao manual das versoes

- Edicao manual tem prioridade sobre texto gerado.
- Backend deve receber os textos finais aprovados.
- Backend deve validar novamente textos vazios, tamanho e posse das contas.
- Backend deve validar preservacao de URLs e demais elementos imutaveis quando
  a edicao manual ocorrer em fluxo de variacao.
- Regerar preview nao deve sobrescrever edicoes manuais sem acao explicita do
  usuario.

## Roadmap de implementacao oficial

1. Finalizar backend.
2. Auditoria de seguranca.
3. Implementar `AIContentVariationService`.
4. Integrar Groq.
5. Adicionar `rendered_text` por `PostAccount`.
6. Implementar obrigatoriedade para 5+ contas.
7. Implementar pre-visualizacao.
8. Implementar edicao manual.
9. Implementar logs, metricas e cache.
10. Testar falhas da Groq.
11. Fazer validacao final.

## Estrategia para futuras evolucoes

Possiveis evolucoes:

- Perfis de tom por conta.
- Templates por nicho.
- Regras de marca por usuario.
- A/B testing de variacoes.
- Agendamento inteligente.
- Suporte a imagem/video/link usando `PublicationContentType`.
- Worker assincromo para geracao longa.
- Auditoria especifica de geracao por IA.
- Metricas de qualidade e taxa de falha por modelo.

## Inconsistencias e lacunas a nao corrigir nesta etapa

- O frontend ainda nao possui fluxo de posts ou contas.
- O backend ainda define schemas de post dentro da rota, embora exista pasta
  `app.schemas`.
- Nao ha testes automatizados observados.
- Esta especificacao nao cria stubs de codigo porque a tarefa atual e
  incorporar o roadmap oficial a documentacao permanente.
- A especificacao anterior preparada antes do roadmap oficial tratava 2 a 4
  contas como cenario de geracao de variacoes. O roadmap oficial corrige essa
  regra: para 2 a 4 contas, publicar texto original; no frontend a Publicacao
  Inteligente e opcional e ativada por padrao, com aviso recomendando
  diversificacao automatica.
