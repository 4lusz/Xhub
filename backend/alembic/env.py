"""
Configuracao do ambiente Alembic.

A URL do banco vem de app.config.settings (que por sua vez le o .env),
entao nao e necessario duplicar a string de conexao no alembic.ini.

Os models devem ser importados aqui (via app.models) para que o
autogenerate consiga detectar as tabelas.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config.settings import settings
from app.database.base import Base

# Importa todos os models para que fiquem registrados em Base.metadata.
# Nesta etapa (1 - infraestrutura) ainda nao existem models de dominio;
# o import abaixo continuara funcionando conforme forem sendo criados
# nas proximas etapas (User, TwitterAccount, Post, etc.).
from app import models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
