# Changelog

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
