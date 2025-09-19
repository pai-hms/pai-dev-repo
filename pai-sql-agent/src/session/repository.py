"""
세션 리포지토리 - 데이터 영속성 관리
통계청 및 SGIS 데이터 분석용 세션 리포지토리 클래스
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager, get_database_manager
from .domains import AgentSession
from .entities import AgentSessionEntity

logger = logging.getLogger(__name__)


class SessionRepository:
    """세션 데이터 영속성 관리 - 직접 구현 (BaseRepository 상속 제거)"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        logger.info("✅ SessionRepository 초기화 완료")
    
    async def create_session(self, session: AgentSession) -> AgentSession:
        """새 세션 생성"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                entity = AgentSessionEntity(
                    session_id=session.session_id,
                    thread_id=session.thread_id,
                    title=session.title,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    last_activity=session.last_activity,
                    message_count=session.message_count,
                    is_active=session.is_active,
                    metadata=session.metadata
                )
                
                db_session.add(entity)
                await db_session.flush()
                await db_session.refresh(entity)
                
                logger.info(f"✅ 세션 생성 완료: {session.session_id}")
                return self._entity_to_domain(entity)
                
        except Exception as e:
            logger.error(f"세션 생성 오류: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """세션 조회"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                stmt = select(AgentSessionEntity).where(
                    AgentSessionEntity.session_id == session_id
                )
                result = await db_session.execute(stmt)
                entity = result.scalar_one_or_none()
                
                if entity:
                    return self._entity_to_domain(entity)
                else:
                    logger.warning(f"세션을 찾을 수 없음: {session_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"세션 조회 오류: {e}")
            return None
    
    async def update_session(self, session: AgentSession) -> bool:
        """세션 업데이트"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                stmt = update(AgentSessionEntity).where(
                    AgentSessionEntity.session_id == session.session_id
                ).values(
                    title=session.title,
                    updated_at=session.updated_at,
                    last_activity=session.last_activity,
                    message_count=session.message_count,
                    is_active=session.is_active,
                    metadata=session.metadata
                )
                
                result = await db_session.execute(stmt)
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"세션 업데이트 오류: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                stmt = delete(AgentSessionEntity).where(
                    AgentSessionEntity.session_id == session_id
                )
                result = await db_session.execute(stmt)
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"세션 삭제 오류: {e}")
            return False
    
    async def get_sessions_by_user(self, user_id: str, active_only: bool = True) -> List[AgentSession]:
        """사용자별 세션 목록 조회"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                stmt = select(AgentSessionEntity).where(
                    AgentSessionEntity.user_id == user_id
                )
                
                if active_only:
                    stmt = stmt.where(AgentSessionEntity.is_active == True)
                
                stmt = stmt.order_by(desc(AgentSessionEntity.last_activity))
                
                result = await db_session.execute(stmt)
                entities = result.scalars().all()
                
                return [self._entity_to_domain(entity) for entity in entities]
                
        except Exception as e:
            logger.error(f"사용자 세션 조회 오류: {e}")
            return []
    
    async def get_recent_sessions(self, limit: int = 20) -> List[AgentSession]:
        """최근 세션 목록 조회"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                stmt = select(AgentSessionEntity).where(
                    AgentSessionEntity.is_active == True
                ).order_by(desc(AgentSessionEntity.last_activity)).limit(limit)
                
                result = await db_session.execute(stmt)
                entities = result.scalars().all()
                
                return [self._entity_to_domain(entity) for entity in entities]
                
        except Exception as e:
            logger.error(f"최근 세션 조회 오류: {e}")
            return []
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """오래된 세션 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            async with self.db_manager.get_async_session() as db_session:
                stmt = delete(AgentSessionEntity).where(
                    and_(
                        AgentSessionEntity.last_activity < cutoff_date,
                        AgentSessionEntity.is_active == False
                    )
                )
                result = await db_session.execute(stmt)
                
                logger.info(f"✅ 오래된 세션 {result.rowcount}개 정리 완료")
                return result.rowcount
                
        except Exception as e:
            logger.error(f"세션 정리 오류: {e}")
            return 0
    
    def _entity_to_domain(self, entity: AgentSessionEntity) -> AgentSession:
        """Entity를 Domain 객체로 변환"""
        return AgentSession(
            session_id=entity.session_id,
            thread_id=entity.thread_id,
            title=entity.title,
            user_id=entity.user_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_activity=entity.last_activity,
            message_count=entity.message_count,
            is_active=entity.is_active,
            metadata=entity.metadata or {}
        )
    
    # 통계 메서드들
    async def get_session_statistics(self) -> Dict[str, Any]:
        """세션 통계 조회"""
        try:
            async with self.db_manager.get_async_session() as db_session:
                # 전체 세션 수
                total_stmt = select(func.count(AgentSessionEntity.id))
                total_result = await db_session.execute(total_stmt)
                total_count = total_result.scalar()
                
                # 활성 세션 수
                active_stmt = select(func.count(AgentSessionEntity.id)).where(
                    AgentSessionEntity.is_active == True
                )
                active_result = await db_session.execute(active_stmt)
                active_count = active_result.scalar()
                
                return {
                    "total_sessions": total_count,
                    "active_sessions": active_count,
                    "inactive_sessions": total_count - active_count,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"세션 통계 조회 오류: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "inactive_sessions": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 헬퍼 함수
async def create_session_repository() -> SessionRepository:
    """세션 리포지토리 생성"""
    db_manager = await get_database_manager()
    return SessionRepository(db_manager)
