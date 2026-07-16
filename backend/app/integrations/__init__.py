"""Clientes de integracao com servicos externos (fora do dominio SQLAlchemy).

Segue o mesmo espirito de `app.oauth`: cada cliente encapsula toda a
comunicacao HTTP com um provedor externo especifico, sem conhecer
models nem regras de negocio.
"""
