"""Alembic environment configuration — async PostgreSQL (asyncpg)."""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context

from app.core.config import settings
from app.core.database import Base
from app.models import models  # noqa: F401 — registers all ORM models

# ── Alembic config object ──────────────────────────────────────────────────────
config = context.config

# Always read DATABASE_URL from environment / .env — never from alembic.ini
# Strip +asyncpg for the sync psycopg2 offline URL; keep it for async online.
_async_url = settings.DATABASE_URL   # postgresql+asyncpg://...
_sync_url  = _async_url.replace("+asyncpg", "")  # postgresql://... (for offline mode)

config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode (generates SQL script, no live DB needed) ────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (runs against live PostgreSQL via asyncpg) ────────────────────
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # Use asyncpg driver for the live connection
    # Render PostgreSQL requires SSL — pass ssl=require via connect_args
    connectable: AsyncEngine = create_async_engine(
        _async_url,
        poolclass=pool.NullPool,  # no pooling during migrations
        connect_args={"ssl": "require"},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


# ── Entry point ────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
