---
name: XHub Core Rules
alwaysApply: true
description: Regras permanentes de engenharia para qualquer tarefa no projeto XHub.
---

# XHub Core Rules

- Antes de alterar codigo, leia os arquivos relevantes do projeto e confirme o padrao existente.
- Preserve a arquitetura em camadas: Routes -> Services -> Repositories -> Models.
- Nao coloque regra de negocio em rotas FastAPI; rotas validam entrada, autorizacao, transacao e serializacao.
- Nao acesse banco diretamente fora de repositories, exceto health checks simples.
- Nao leia `os.environ` diretamente; use `app.config.settings.settings`.
- Nao quebre idempotencia de publicacao: uma conta ja publicada com sucesso nao deve ser republicada em retries.
- Nao faca chamadas externas irreversiveis antes de validar assinatura, saldo e posse dos recursos.
- Use excecoes de `app.core.exceptions` para erros esperados de dominio/aplicacao.
- Preserve tokens OAuth criptografados em repouso.
- Se houver divergencia entre README, roadmap e codigo, trate o codigo como fonte do estado implementado e documente a divergencia.
- Nao implemente funcionalidades planejadas sem consultar `.continue/context/ROADMAP.md` e `docs/`.
