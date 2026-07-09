# Base de conhecimento do XHub para Continue.dev

Esta pasta guarda contexto permanente para a extensao Continue.dev no VS Code.
Ela foi organizada para que a IA consiga entender rapidamente o projeto sem
depender de explicacoes repetidas em chat.

## Estrutura

```text
.continue/
+-- README.md
+-- context/
|   +-- XHUB_CONTEXT.md
|   +-- ROADMAP.md
+-- rules/
    +-- 01-xhub-core.md
    +-- 02-backend-python.md
    +-- 03-frontend-react.md
```

## Como o Continue usa isto

- Arquivos em `.continue/rules` sao regras de sistema do Continue.
- Arquivos em `.continue/context` sao documentacao permanente para ser anexada
  como contexto quando a IA precisar entender dominio, arquitetura ou roadmap.
- O roadmap e tratado como fonte viva: ao mudar o produto, atualize
  `.continue/context/ROADMAP.md` e, se necessario, os documentos em `docs/`.

## Manutencao

Mantenha poucos arquivos, com informacao tecnica de alta densidade. Evite
duplicar conteudo entre regras e contexto: regras dizem como agir; contexto
explica o projeto.
