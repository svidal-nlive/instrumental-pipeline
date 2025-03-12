import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
from app.models import Base

# Load config
config = context.config

# Interpret the config file for logging
fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

# Database URL from environment
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

def run_migrations_online():
    """Run migrations in online mode."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(context.configure, connection=connection, target_metadata=target_metadata)
        await connection.run_sync(context.run_migrations)

run_migrations_online()
