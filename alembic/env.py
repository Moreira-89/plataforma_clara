from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Importar os modelos registra as tabelas em SQLModel.metadata. Sem este import o
# autogenerate enxerga um metadata vazio e propõe apagar o banco inteiro.
from plataforma_clara.domain import models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadados usados pelo autogenerate. Antes da Fase 1 os modelos herdavam de
# `rx.Model` e as migrações eram geradas pelo `reflex db migrate`; agora são
# SQLModel puro e o Alembic é usado direto.
#
# AVISO: o histórico em versions/ NÃO reproduz o schema atual — a migração que cria
# `tb_usuario` declara as colunas `nome`, `email` e `senha_hash`, e nenhuma migração
# posterior as renomeia para `nome_usuario`, `email_usuario` e `senha_hash_usuario`.
# Um autogenerate contra um banco vazio vai propor mudanças que não batem com o
# Supabase em uso. Confira o diff proposto antes de aplicar qualquer migração nova.
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
