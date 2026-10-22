from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

moteur = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)

with moteur.connect() as connexion:
    context.configure(connection=connexion)
    with context.begin_transaction():
        context.run_migrations()
