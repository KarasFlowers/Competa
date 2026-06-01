from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def create_tables() -> None:
    from app.models.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration: add columns that create_all won't add
        # to existing tables (SQLite limitation).
        await _migrate_add_columns(conn)


async def _migrate_add_columns(conn) -> None:
    """Add columns that may be missing from existing tables."""
    migrations = [
        ("sources", "reliability_score", "FLOAT DEFAULT 0.5"),
    ]
    for table, column, col_type in migrations:
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        except Exception:
            # Column already exists or table doesn't exist — safe to ignore
            pass
