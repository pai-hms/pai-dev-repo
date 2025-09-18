"""
데이터베이스 연결 관리
비동기 및 동기 연결을 모두 지원하는 데이터베이스 매니저 클래스
"""
import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.config.settings import get_settings
from src.database.entities import Base  # models → entities 변경


class DatabaseManager:
    """데이터베이스 연결 매니저"""
    
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
            # PostgreSQL URL을 asyncpg 드라이버용으로 변환
            async_url = self.settings.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            self._async_engine = create_async_engine(
                async_url,
                poolclass=StaticPool,
                pool_pre_ping=True,
                echo=False,
                future=True
            )
        return self._async_engine
    
    @property
    def sync_engine(self) -> Engine:
        """동기 엔진 반환"""
        if self._sync_engine is None:
            # PostgreSQL URL을 psycopg2 드라이버용으로 변환 (기본)
            sync_url = self.settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
            
            self._sync_engine = create_engine(
                sync_url,
                poolclass=StaticPool,
                pool_pre_ping=True,
                echo=False,
                future=True
            )
        return self._sync_engine
    
    @property
    def async_session_factory(self) -> sessionmaker:
        """비동기 세션 팩토리 반환"""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    @property
    def sync_session_factory(self) -> sessionmaker:
        """동기 세션 팩토리 반환"""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                expire_on_commit=False
            )
        return self._sync_session_factory
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """비동기 세션 컨텍스트 매니저"""
        session_factory = self.async_session_factory
        async with session_factory() as session:
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
        """동기 세션 컨텍스트 매니저 (비동기 컨텍스트)"""
        session_factory = self.sync_session_factory
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def create_tables(self):
        """테이블 생성 (비동기)"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    def create_tables_sync(self):
        """테이블 생성 (동기)"""
        Base.metadata.create_all(self.sync_engine)
    
    async def drop_tables(self):
        """테이블 삭제 (비동기)"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    def drop_tables_sync(self):
        """테이블 삭제 (동기)"""
        Base.metadata.drop_all(self.sync_engine)
    
    async def execute_raw_sql(self, sql: str, **params):
        """원시 SQL 실행 (비동기)"""
        async with self.get_async_session() as session:
            result = await session.execute(text(sql), params)
            return result
    
    def execute_raw_sql_sync(self, sql: str, **params):
        """원시 SQL 실행 (동기)"""
        with self.sync_session_factory() as session:
            result = session.execute(text(sql), params)
            session.commit()
            return result
    
    async def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    async def cleanup(self):
        """연결 정리"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()


# 전역 데이터베이스 매니저 인스턴스
_db_manager: Optional[DatabaseManager] = None
_db_lock = asyncio.Lock()


async def get_database_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환 (비동기 싱글톤)"""
    global _db_manager
    if _db_manager is None:
        async with _db_lock:
            if _db_manager is None:
                _db_manager = DatabaseManager()
    return _db_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 세션 헬퍼 함수"""
    db_manager = await get_database_manager()
    async with db_manager.get_async_session() as session:
        yield session


# 하위 호환성을 위한 동기 함수 (DEPRECATED)
def get_database_manager_sync() -> DatabaseManager:
    """
    DEPRECATED: 동기 데이터베이스 매니저 반환
    새 코드에서는 get_database_manager() 사용
    """
    import warnings
    warnings.warn(
        "get_database_manager_sync()는 deprecated입니다. "
        "get_database_manager()를 사용하세요.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # 이미 초기화된 인스턴스가 있다면 반환
    global _db_manager
    if _db_manager is not None:
        return _db_manager
    
    # 없다면 새로 생성 (하위 호환성)
    return DatabaseManager()