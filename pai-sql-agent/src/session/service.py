"""
세션 서비스 - 멀티턴 대화 관리
멀티턴 대화 세션을 관리하는 서비스
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .domains import AgentSession, SessionContext
from .repository import SessionRepository

logger = logging.getLogger(__name__)


class SessionService:
    """SQL Agent 세션 관리 서비스"""
    
    def __init__(self, session_repository: SessionRepository):
        self.repository = session_repository
        logger.info("SessionService 초기화 완료")
    
    async def start_new_session(
        self, 
        title: str, 
        user_id: Optional[str] = None,
        custom_thread_id: Optional[str] = None
    ) -> AgentSession:
        """새 세션 시작"""
        session = AgentSession.new(
            title=title, 
            user_id=user_id,
            custom_thread_id=custom_thread_id
        )
        
        # 데이터베이스에 저장
        saved_session = await self.repository.save(session)
        logger.info(f"새 세션 생성: {saved_session.session_id}")
        
        return saved_session
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """세션 ID로 세션 조회"""
        return await self.repository.find_by_id(session_id)
    
    async def get_session_by_thread_id(self, thread_id: str) -> Optional[AgentSession]:
        """스레드 ID로 세션 조회"""
        return await self.repository.find_by_thread_id(thread_id)
    
    async def get_or_create_session(
        self,
        thread_id: str,
        title: str,
        user_id: Optional[str] = None
    ) -> AgentSession:
        """
        세션 조회하거나 없으면 생성
        
        Args:
            thread_id: 스레드 ID
            title: 세션 제목 (새로 생성할 때 사용)
            user_id: 사용자 ID (선택적)
            
        Returns:
            AgentSession: 기존 세션 또는 새로 생성된 세션
        """
        # 기존 세션 조회
        existing_session = await self.get_session_by_thread_id(thread_id)
        
        if existing_session:
            logger.info(f"기존 세션 발견: {existing_session.session_id}")
            return existing_session
        
        # 새 세션 생성
        logger.info(f"새 세션 생성: thread_id={thread_id}")
        return await self.start_new_session(
            title=title,
            user_id=user_id,
            custom_thread_id=thread_id
        )
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentSession]:
        """사용자의 세션 목록 조회"""
        return await self.repository.find_by_user_id(user_id, limit, offset)
    
    async def get_recent_sessions(
        self, 
        limit: int = 10,
        offset: int = 0
    ) -> List[AgentSession]:
        """최근 세션 목록 조회"""
        return await self.repository.find_recent_sessions(limit, offset)
    
    async def update_session_activity(
        self, 
        session_id: str, 
        increment_message: bool = False
    ) -> Optional[AgentSession]:
        """세션 활동 업데이트"""
        session = await self.repository.find_by_id(session_id)
        if not session:
            return None
        
        # 활동 시간 업데이트
        session.update_activity()
        
        if increment_message:
            session.increment_message_count()
        
        # 데이터베이스 업데이트
        updated_session = await self.repository.update(session)
        logger.info(f"세션 활동 업데이트: {session_id}")
        
        return updated_session
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        success = await self.repository.delete(session_id)
        if success:
            logger.info(f"세션 삭제: {session_id}")
        return success
    
    async def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """세션 컨텍스트 조회"""
        session = await self.repository.find_by_id(session_id)
        if not session:
            return None
        
        return SessionContext(
            session_id=session.session_id,
            thread_id=session.thread_id,
            title=session.title,
            user_id=session.user_id,
            message_count=session.message_count,
            created_at=session.created_at,
            last_activity=session.last_activity
        )
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """오래된 세션 정리"""
        deleted_count = await self.repository.delete_old_sessions(days_old)
        logger.info(f"오래된 세션 {deleted_count}개 삭제")
        return deleted_count


# 글로벌 세션 서비스 인스턴스
_session_service: Optional[SessionService] = None


async def get_session_service() -> Optional[SessionService]:
    """세션 서비스 인스턴스 반환 (싱글톤)"""
    global _session_service
    if _session_service is None:
        try:
            from .container import get_session_container
            container = await get_session_container()
            _session_service = await container.get("session_service")
            logger.info("✅ 세션 서비스 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 세션 서비스 초기화 실패: {e}")
            return None
    return _session_service
