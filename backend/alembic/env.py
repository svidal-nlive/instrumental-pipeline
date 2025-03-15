import os
import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Add the project root to sys.path so that "app" is importable.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment variables from the project root .env file.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

# Use the DATABASE_URL from the environment
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/pipeline_db")
config.set_main_option("sqlalchemy.url", database_url)

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(
        database_url,
        echo=True,
        poolclass=pool.NullPool,
        future=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    url = database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
