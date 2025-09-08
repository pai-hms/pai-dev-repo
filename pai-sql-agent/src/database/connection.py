"""Database connection management module."""

import asyncio
from typing import AsyncGenerator

import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

# SQLAlchemy Base
Base = declarative_base()

# Async SQLAlchemy Engine
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync SQLAlchemy Engine (for migrations)
sync_engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


class DatabaseManager:
    """Database connection manager following data sovereignty principle."""
    
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        self._pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
        )
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection from pool."""
        if not self._pool:
            await self.initialize()
        return await self._pool.acquire()
    
    async def release_connection(self, connection: asyncpg.Connection) -> None:
        """Release database connection back to pool."""
        if self._pool:
            await self._pool.release(connection)
    
    async def execute_query(self, query: str, *args) -> list[dict]:
        """Execute SQL query and return results."""
        connection = await self.get_connection()
        try:
            result = await connection.fetch(query, *args)
            return [dict(row) for row in result]
        finally:
            await self.release_connection(connection)


# Global database manager instance
db_manager = DatabaseManager()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency to get raw database connection."""
    connection = await db_manager.get_connection()
    try:
        yield connection
    finally:
        await db_manager.release_connection(connection)
