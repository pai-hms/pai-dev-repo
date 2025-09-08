"""
데이터베이스 연결 관리
데이터 주권 원칙에 따라 데이터베이스 연결의 제어권을 담당
"""
import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.config.settings import get_settings
from src.database.models import Base


class DatabaseManager:
    """데이터베이스 연결 관리자"""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine: Optional[Engine] = None
        self._async_session_factory: Optional[sessionmaker] = None
        self._sync_session_factory: Optional[sessionmaker] = None
    
    @property
    def async_engine(self) -> AsyncEngine:
        """비동기 엔진 반환"""
        if self._async_engine is None:
            # PostgreSQL URL을 asyncpg용으로 변환
            async_url = self.settings.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self._async_engine = create_async_engine(
                async_url,
                echo=self.settings.debug,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
        return self._async_engine
    
    @property
    def sync_engine(self) -> Engine:
        """동기 엔진 반환"""
        if self._sync_engine is None:
            # PostgreSQL URL을 psycopg2용으로 변환
            sync_url = self.settings.database_url.replace(
                "postgresql://", "postgresql+psycopg2://"
            )
            self._sync_engine = create_engine(
                sync_url,
                echo=self.settings.debug,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
        return self._sync_engine
    
    @property
    def async_session_factory(self) -> sessionmaker:
        """비동기 세션 팩토리 반환"""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._async_session_factory
    
    @property
    def sync_session_factory(self) -> sessionmaker:
        """동기 세션 팩토리 반환"""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                class_=Session,
                expire_on_commit=False,
            )
        return self._sync_session_factory
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """비동기 세션 컨텍스트 매니저"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def get_sync_session(self) -> AsyncGenerator[Session, None]:
        """동기 세션 컨텍스트 매니저 (비동기 컨텍스트에서 사용)"""
        with self.sync_session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    async def create_tables(self) -> None:
        """테이블 생성"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self) -> None:
        """테이블 삭제"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def close(self) -> None:
        """연결 종료"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()


# 전역 데이터베이스 매니저 인스턴스
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환 (싱글톤)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 세션 의존성 주입용 함수"""
    db_manager = get_database_manager()
    async with db_manager.get_async_session() as session:
        yield session