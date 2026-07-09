---
name: XHub Backend Python Rules
globs: ["backend/**/*.py"]
description: Padroes do backend FastAPI/SQLAlchemy do XHub.
---

# Backend Rules

- Use Python com tipagem explicita nos limites publicos de classes e funcoes.
- Models SQLAlchemy devem herdar de `Base` e, quando aplicavel, `TimestampMixin`.
- IDs persistidos seguem UUID.
- Enums persistidos ficam em `app.models.enums` quando representam estado de banco.
- Regras puras de dominio ficam em `app.domain`; orquestracao transacional fica em services.
- Services recebem repositories e clientes externos por injecao no construtor.
- Dependencies FastAPI em `app.auth.dependencies` montam services e clientes.
- Rotas devem capturar `BaseAppException`, fazer rollback quando houver transacao e converter para HTTP.
- Migrations Alembic sao obrigatorias para qualquer mudanca de schema.
- Chamada externa ao X ou a qualquer IA deve ficar encapsulada em cliente/service especifico, nunca espalhada em rota.
- Repositories devem retornar models ou sequencias de models e encapsular queries SQLAlchemy.
- Preserve mensagens de erro em portugues, no estilo atual do projeto.
