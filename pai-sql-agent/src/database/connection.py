"""
데이터베이스 연결 관리 - 비동기 전용
한국 통계청 데이터 분석을 위한 비동기 데이터베이스 매니저
"""
import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.settings import get_settings
from src.database.entities import Base


class DatabaseManager:
    """비동기 데이터베이스 연결 매니저"""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self._async_engine: Optional[AsyncEngine] = None
        self._async_session_factory: Optional[sessionmaker] = None
    
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
    def async_session_factory(self) -> sessionmaker:
        """비동기 세션 팩토리 반환"""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory
    
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
    
    # 추가: get_session 메서드 (별칭)
    def get_session(self):
        """세션 컨텍스트 매니저 (별칭)"""
        return self.get_async_session()
    
    async def create_tables(self):
        """테이블 생성"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """테이블 삭제"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def execute_raw_sql(self, sql: str, **params):
        """원시 SQL 실행"""
        async with self.get_async_session() as session:
            result = await session.execute(text(sql), params)
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