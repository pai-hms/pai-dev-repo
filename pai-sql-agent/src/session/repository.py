"""
세션 리포지토리 - 데이터 영속성 관리
통계청 및 SGIS 데이터 분석용 세션 리포지토리 클래스
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager
from src.database.repository import BaseRepository
from .domains import AgentSession
from .entities import AgentSessionEntity

logger = logging.getLogger(__name__)


class SessionRepository:
    """세션 리포지토리"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.entity_class = AgentSessionEntity
    
    async def save(self, session: AgentSession) -> AgentSession:
        """세션 저장"""
        async with self.db_manager.get_async_session() as db_session:
            entity = self._domain_to_entity(session)
            db_session.add(entity)
            await db_session.flush()
            await db_session.refresh(entity)
            return self._entity_to_domain(entity)
    
    async def find_by_id(self, session_id: str) -> Optional[AgentSession]:
        """세션 ID로 조회"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = select(self.entity_class).where(
                self.entity_class.session_id == session_id
            )
            result = await db_session.execute(stmt)
            entity = result.scalar_one_or_none()
            
            if entity:
                return self._entity_to_domain(entity)
            return None
    
    async def find_by_thread_id(self, thread_id: str) -> Optional[AgentSession]:
        """스레드 ID로 조회"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = select(self.entity_class).where(
                self.entity_class.thread_id == thread_id
            )
            result = await db_session.execute(stmt)
            entity = result.scalar_one_or_none()
            
            if entity:
                return self._entity_to_domain(entity)
            return None
    
    async def find_by_user_id(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[AgentSession]:
        """사용자 ID로 세션 목록 조회"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = (
                select(self.entity_class)
                .where(self.entity_class.user_id == user_id)
                .order_by(desc(self.entity_class.last_activity))
                .limit(limit)
                .offset(offset)
            )
            result = await db_session.execute(stmt)
            entities = result.scalars().all()
            
            return [self._entity_to_domain(entity) for entity in entities]
    
    async def find_recent_sessions(
        self, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[AgentSession]:
        """최근 세션 목록 조회"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = (
                select(self.entity_class)
                .order_by(desc(self.entity_class.last_activity))
                .limit(limit)
                .offset(offset)
            )
            result = await db_session.execute(stmt)
            entities = result.scalars().all()
            
            return [self._entity_to_domain(entity) for entity in entities]
    
    async def update(self, session: AgentSession) -> AgentSession:
        """세션 업데이트"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = (
                update(self.entity_class)
                .where(self.entity_class.session_id == session.session_id)
                .values(
                    title=session.title,
                    message_count=session.message_count,
                    last_activity=session.last_activity,
                    is_active=session.is_active,
                    settings=session.metadata
                )
                .returning(self.entity_class)
            )
            result = await db_session.execute(stmt)
            entity = result.scalar_one()
            
            return self._entity_to_domain(entity)
    
    async def delete(self, session_id: str) -> bool:
        """세션 삭제"""
        async with self.db_manager.get_async_session() as db_session:
            stmt = delete(self.entity_class).where(
                self.entity_class.session_id == session_id
            )
            result = await db_session.execute(stmt)
            return result.rowcount > 0
    
    async def delete_old_sessions(self, days_old: int = 30) -> int:
        """오래된 세션 삭제"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        async with self.db_manager.get_async_session() as db_session:
            stmt = delete(self.entity_class).where(
                self.entity_class.last_activity < cutoff_date
            )
            result = await db_session.execute(stmt)
            return result.rowcount
    
    def _domain_to_entity(self, session: AgentSession) -> AgentSessionEntity:
        """도메인 -> 엔티티 변환"""
        return AgentSessionEntity(
            session_id=session.session_id,
            thread_id=session.thread_id,
            title=session.title,
            user_id=session.user_id,
            message_count=session.message_count,
            created_at=session.created_at,
            last_activity=session.last_activity,
            is_active=session.is_active,
            settings=session.metadata
        )
    
    def _entity_to_domain(self, entity: AgentSessionEntity) -> AgentSession:
        """엔티티 -> 도메인 변환"""
        return AgentSession(
            session_id=entity.session_id,
            thread_id=entity.thread_id,
            title=entity.title,
            user_id=entity.user_id,
            message_count=entity.message_count,
            created_at=entity.created_at,
            last_activity=entity.last_activity,
            is_active=entity.is_active,
            metadata=entity.settings or {}
        )


# 헬퍼 함수 (하위 호환성)
async def create_session_repository() -> SessionRepository:
    """세션 리포지토리 생성"""
    from src.database.connection import get_database_manager
    db_manager = await get_database_manager()
    return SessionRepository(db_manager)
