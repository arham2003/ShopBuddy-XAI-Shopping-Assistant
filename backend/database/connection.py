"""
database/connection.py — Async SQLAlchemy engine connected to Supabase PostgreSQL.

Converts the standard Supabase connection string to the asyncpg driver prefix
and exposes an async session factory + init_db() for table creation.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from config import settings


# ---------------------------------------------------------------------------
# Build the async-compatible connection URL from the Supabase-provided string
# ---------------------------------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# NOTE: If you are using Supabase's Transaction-mode pooler (port 6543),
# uncomment the block below to disable asyncpg's prepared-statement cache,
# which pgbouncer/Supavisor does not support in transaction mode.
# Session-mode pooler (port 5432) works without this.
#
# from sqlalchemy.pool import NullPool
# engine = create_async_engine(
#     DATABASE_URL,
#     echo=False,
#     poolclass=NullPool,
#     connect_args={"prepared_statement_cache_size": 0},
# )

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative base for all ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependency — yields an async session (for FastAPI Depends())
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_maker() as session:
        yield session


# ---------------------------------------------------------------------------
# init_db — create all tables that don't yet exist in Supabase
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """
    Called once during FastAPI startup (lifespan).
    Uses Base.metadata.create_all to issue CREATE TABLE IF NOT EXISTS
    for every registered ORM model.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
