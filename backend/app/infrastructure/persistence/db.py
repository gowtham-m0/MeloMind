"""The async database engine and sessions for Supabase Postgres."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """An asyncpg engine. `DATABASE_URL` looks like `postgresql+asyncpg://user:pass@host:5432/db`.

    Prepared statements are off so the engine also works through Supabase's pooler.
    """
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions whose objects stay readable after commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
