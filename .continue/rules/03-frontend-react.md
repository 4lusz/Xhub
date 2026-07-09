---
name: XHub Frontend React Rules
globs: ["frontend/**/*.{ts,tsx,css}"]
description: Padroes do frontend React/Vite do XHub.
---

# Frontend Rules

- Use React, TypeScript, Vite, TailwindCSS, Axios e TanStack Query conforme stack atual.
- Centralize chamadas HTTP em `frontend/src/services`.
- Modele tipos compartilhados em `frontend/src/types`.
- Prefira hooks para consultas e mutacoes reutilizaveis.
- Preserve UI objetiva e operacional; XHub e um SaaS de gestao, nao uma landing page.
- Nao crie telas ou fluxos ficticios sem API correspondente ou especificacao em `docs/`.
- Valide estados de carregamento, erro e sucesso em componentes que consomem API.
