"""
Database Session Factory - 세션 팩토리 패턴
DI 기반 세션 관리 및 생명주기 제어
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional, Callable
from contextlib import AbstractContextManager, asynccontextmanager

import sqlalchemy
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncEngine, 
    AsyncSession,
    async_scoped_session,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, StaticPool

from .settings import DatabaseSettings
from .entities import Base

logger = logging.getLogger(__name__)


class DatabaseSessionFactory:
    """비동기 데이터베이스 세션 팩토리"""
    
    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._scoped_session: Optional[async_scoped_session] = None
        
    @property
    def engine(self) -> AsyncEngine:
        """비동기 엔진 반환 (지연 생성)"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    def _create_engine(self) -> AsyncEngine:
        """데이터베이스 엔진 생성"""
        if self.settings.DB_TYPE.startswith("sqlite"):
            # SQLite 설정
            engine = create_async_engine(
                self.settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
                poolclass=StaticPool,
                echo=self.settings.DB_ECHO,
                future=True
            )
        elif self.settings.DB_TYPE.startswith("postgresql"):
            # PostgreSQL 설정
            async_url = self.settings.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            engine = create_async_engine(
                async_url,
                poolclass=NullPool,  # NullPool 사용 시 pool 관련 설정 제거
                echo=self.settings.DB_ECHO,
                future=True
            )
        else:
            raise ValueError(f"지원하지 않는 데이터베이스 타입: {self.settings.DB_TYPE}")
        
        logger.info(f"데이터베이스 엔진 생성 완료: {self.settings.DB_TYPE}")
        return engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """세션 팩토리 반환"""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                autocommit=self.settings.DB_AUTOCOMMIT,
                autoflush=self.settings.DB_AUTOFLUSH,
                expire_on_commit=self.settings.DB_EXPIRE_ON_COMMIT
            )
        return self._session_factory
    
    @property
    def scoped_session(self) -> async_scoped_session:
        """스코프 세션 반환 (태스크별 격리)"""
        if self._scoped_session is None:
            self._scoped_session = async_scoped_session(
                self.session_factory,
                scopefunc=asyncio.current_task  # 태스크별 세션 스코프
            )
        return self._scoped_session
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """세션 컨텍스트 매니저 (자동 예외 처리)"""
        session: AsyncSession = self.session_factory()
        try:
            yield session
            await session.commit()
        except sqlalchemy.exc.NoResultFound:
            await session.rollback()
            logger.warning("데이터를 찾을 수 없습니다")
            raise
        except sqlalchemy.exc.IntegrityError as e:
            await session.rollback()
            logger.error(f"데이터 무결성 오류: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.exception(f"세션 오류로 인한 롤백: {e}")
            raise
        finally:
            await session.close()
    
    @asynccontextmanager
    async def get_scoped_session(self) -> AsyncGenerator[AsyncSession, None]:
        """스코프 세션 컨텍스트 매니저"""
        session: AsyncSession = self.scoped_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception(f"스코프 세션 오류: {e}")
            raise
        finally:
            await session.close()
            await self.scoped_session.remove()
    
    async def create_tables(self):
        """데이터베이스 테이블 생성"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("데이터베이스 테이블 생성 완료")
    
    async def drop_tables(self):
        """데이터베이스 테이블 삭제"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("데이터베이스 테이블 삭제 완료")
    
    async def close(self):
        """엔진 정리"""
        if self._engine:
            await self._engine.dispose()
            logger.info("데이터베이스 엔진 정리 완료")
    
    def __call__(self) -> Callable[..., AbstractContextManager[AsyncSession]]:
        """호출 가능한 세션 팩토리 반환 (Repository 패턴용)"""
        return self.get_session
