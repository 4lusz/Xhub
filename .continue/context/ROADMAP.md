# XHub - Roadmap permanente para IA

Este arquivo deve ser mantido como contexto vivo para Continue.dev.

## Estado do roadmap fornecido

O roadmap oficial da funcionalidade Publicacao Inteligente foi fornecido pelo
usuario e incorporado oficialmente a esta base permanente de conhecimento.

Fonte oficial incorporada:

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

Roadmap
1. Finalizar backend.
2. Auditoria de seguranca.
3. Implementar AIContentVariationService.
4. Integrar Groq.
5. rendered_text por PostAccount.
6. Obrigatoriedade para 5+ contas.
7. Pre-visualizacao.
8. Edicao manual.
9. Logs, metricas e cache.
10. Testar falhas da Groq.
11. Validacao final.

Especificacao
Este documento e a especificacao oficial da funcionalidade e deve ser seguido
pela IA responsavel pela implementacao, preservando a arquitetura atual do
XHub e evitando refatoracoes desnecessarias.
```

## Implementado conforme codigo atual

- Backend FastAPI com arquitetura em camadas.
- PostgreSQL com SQLAlchemy 2.0 e Alembic.
- Autenticacao JWT.
- Roles `client` e `admin`.
- Criacao administrativa de usuarios com assinatura explicita.
- Planos e assinaturas.
- Controle de limite de contas conectadas.
- Controle de saldo de posts.
- Posts extras.
- Auditoria administrativa.
- OAuth2 do X com PKCE.
- Criptografia de tokens OAuth em repouso.
- Conexao, listagem e desconexao de contas do X.
- Criacao e publicacao de posts em multiplas contas.
- Idempotencia por `PostAccount`.
- Health check de API e banco.
- Frontend inicial de health check.

## Planejado / especificado

- Publicacao Inteligente como camada que gera variacoes naturais entre
  publicacoes, preserva o significado original e reduz conteudo repetitivo.
- Uso exclusivo da API da Groq para geracao de variacoes; nao usar OpenAI para
  esta funcionalidade.
- Criacao de `AIContentVariationService`.
- Campo `rendered_text` proprio em cada `PostAccount`.
- Preservacao permanente do texto original em `Post.text`.
- Registro de modelo, tempo, tokens, custo quando aplicavel e versao do prompt.
- Cache de variacoes.
- Tratamento explicito de indisponibilidade da Groq.
- Botao "Publicacao Inteligente" no frontend.
- Ate 4 contas: funcionalidade opcional e ativada por padrao no frontend.
- Ate 4 contas: backend pode publicar texto original; a variacao nao e
  obrigatoria.
- Exibicao de aviso recomendando a funcionalidade para diversificar
  automaticamente as publicacoes.
- Com 5 ou mais contas: variacoes obrigatorias.
- Modal de pre-visualizacao.
- Edicao manual das versoes.
- Logs, metricas e cache.
- Testes especificos para falhas da Groq.
- Validacao final da funcionalidade.

## Nao implementado ou nao observado

- Integracao com Groq.
- `AIContentVariationService`.
- `PostAccount.rendered_text`.
- Registro persistente ou estruturado de modelo, tempo, tokens, custo e versao
  do prompt para variacoes de IA.
- Cache de variacoes de IA.
- APIs de preview/geracao de variacoes.
- Regra obrigatoria de 5+ contas no backend.
- Modal frontend de Publicacao Inteligente.
- Botao "Publicacao Inteligente" no frontend.
- Aviso de recomendacao da funcionalidade no frontend.
- Edicao manual de variacoes no frontend.
- Tela completa de posts/contas/assinaturas no frontend.
- Testes automatizados.
- Testes de indisponibilidade da Groq.
- Worker/background job para agendamento/publicacao assincroma.

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

## Decisoes tecnicas oficiais

- A funcionalidade deve preservar a arquitetura atual do XHub.
- Evitar refatoracoes desnecessarias.
- Usar Groq, nao OpenAI.
- `Post.text` guarda sempre o texto original.
- Cada `PostAccount` deve possuir seu proprio `rendered_text`.
- Para 1 conta, publicar texto original.
- Para 2 a 4 contas, publicar texto original como regra de negocio; no
  frontend, a Publicacao Inteligente e opcional e ativada por padrao.
- Para 5 contas ou mais, a geracao de variacoes e obrigatoria.
- Com 5+ contas, se a Groq estiver indisponivel, interromper antes de enviar
  qualquer publicacao ao X.
- Nunca fazer fallback automatico para publicar o mesmo texto em multiplas
  contas quando a regra exigir variacoes.
- O usuario deve poder tentar novamente, salvar como rascunho ou reagendar a
  publicacao quando a Groq estiver indisponivel em fluxo obrigatorio.
- O prompt deve preservar exatamente o significado.
- O prompt deve manter hashtags, @mencoes, emojis e CTA.
- Links e URLs sao constantes imutaveis.
- Nunca expandir, resumir, reescrever, trocar parametros, alterar dominios,
  modificar encurtadores ou qualquer parte da URL.
- O link deve ser preservado exatamente como enviado pelo usuario.

## Divergencias conhecidas

- README antigo estava inconsistente com o codigo: dizia que nao havia rotas de
  negocio, repositories ou services. O codigo atual ja possui essas camadas.
- A especificacao anterior preparada antes do roadmap oficial tratava 2 a 4
  contas como cenario de geracao de variacoes. O roadmap oficial corrige essa
  regra: para 2 a 4 contas, publicar texto original; no frontend a Publicacao
  Inteligente e opcional e ativada por padrao, com aviso recomendando
  diversificacao automatica.
