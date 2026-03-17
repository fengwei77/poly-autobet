"""
Data: Async database connection and session management.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from loguru import logger

from config.settings import settings
from data.models import Base


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"✅ Database initialized: {settings.database_url.split('///')[-1] if '///' in settings.database_url else settings.database_url}")


async def get_session() -> AsyncSession:
    """Get a new async session."""
    async with async_session() as session:
        return session


async def close_db() -> None:
    """Dispose engine connections."""
    await engine.dispose()
    logger.info("Database connections closed.")
