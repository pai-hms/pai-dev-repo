"""
세션 서비스 - 멀티턴 대화 관리
멀티턴 대화 세션을 관리하는 서비스 - Repository 중심 아키텍처
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .domains import AgentSession, SessionContext
from .repository import create_session_repository

logger = logging.getLogger(__name__)


class SessionService:
    """세션 관리 서비스"""
    
    def __init__(self, repository):
        self.repository = repository
        logger.info("✅ SessionService 초기화 완료")
    
    async def create_session(self, user_id: str = "default", session_type: str = "default", session_id: str = None) -> AgentSession:
        """새 세션 생성"""
        try:
            # ✅ session_id가 전달되면 그것을 그대로 사용, 없으면 새로 생성
            if session_id:
                final_session_id = session_id  # 전달받은 ID 그대로 사용
                thread_id = session_id
            else:
                final_session_id = f"session_{user_id}_{int(datetime.now().timestamp())}"
                thread_id = final_session_id
            
            session = AgentSession(
                session_id=final_session_id,  # ✅ 전달받은 ID 또는 새 ID
                thread_id=thread_id,
                title=f"대화 세션 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                user_id=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            saved_session = await self.repository.create_session(session)
            logger.info(f"✅ 새 세션 생성: {saved_session.session_id}")
            return saved_session
            
        except Exception as e:
            logger.error(f"세션 생성 오류: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """세션 조회"""
        try:
            return await self.repository.get_session(session_id)
        except Exception as e:
            logger.error(f"세션 조회 오류: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """세션 활동 시간 업데이트"""
        try:
            session = await self.repository.get_session(session_id)
            if not session:
                return False
            
            session.update_activity()
            await self.repository.update_session(session)
            return True
            
        except Exception as e:
            logger.error(f"세션 활동 업데이트 오류: {e}")
            return False
    
    # ✅ SessionContext 생성 함수 수정 - session_id 직접 사용
    async def create_session_context(self, session_id: str, current_message: str) -> Optional[SessionContext]:
        """세션 컨텍스트 생성 - 대화 히스토리 포함"""
        try:
            session = await self.get_session(session_id)
            if not session:
                # ✅ 세션이 없으면 전달받은 session_id로 새로 생성
                session = await self.create_session(
                    user_id="default", 
                    session_type="default",
                    session_id=session_id  # ✅ 라우터에서 받은 ID 그대로 사용
                )
            
            # 기존 메시지 로드
            messages = await self.get_session_messages(session_id, limit=50)
            
            context = SessionContext(
                session=session,
                current_message=current_message,
                conversation_history=messages
            )
            
            return context
            
        except Exception as e:
            logger.error(f"세션 컨텍스트 생성 오류: {e}")
            return None
    
    # ✅ add_message_to_session 메서드 추가
    async def add_message_to_session(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """세션에 메시지 추가 - agent/nodes.py에서 호출하는 메서드"""
        return await self.add_message(session_id, role, content, metadata)
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """세션에 메시지 추가"""
        try:
            session = await self.repository.get_session(session_id)
            if not session:
                logger.warning(f"세션을 찾을 수 없음: {session_id}")
                return False
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # TODO: 실제 메시지 저장 로직 구현
            session.increment_message_count()
            await self.repository.update_session(session)
            
            logger.info(f"✅ 메시지 추가 완료: {session_id} ({role})")
            return True
            
        except Exception as e:
            logger.error(f"메시지 추가 오류: {e}")
            return False
    
    async def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """세션 메시지 목록 조회"""
        try:
            # TODO: 실제 메시지 저장/조회 로직 구현
            # 현재는 빈 목록 반환
            return []
            
        except Exception as e:
            logger.error(f"세션 메시지 조회 오류: {e}")
            return []
    
    async def close_session(self, session_id: str) -> bool:
        """세션 종료"""
        try:
            session = await self.repository.get_session(session_id)
            if not session:
                logger.warning(f"세션을 찾을 수 없음: {session_id}")
                return False
            
            session.is_active = False
            session.update_activity()
            await self.repository.update_session(session)
            
            logger.info(f"✅ 세션 종료: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"세션 종료 오류: {e}")
            return False
    
    async def get_active_sessions_by_user(self, user_id: str) -> List[AgentSession]:
        """사용자의 활성 세션 목록 조회"""
        try:
            return await self.repository.get_sessions_by_user(user_id, active_only=True)
        except Exception as e:
            logger.error(f"활성 세션 조회 오류: {e}")
            return []


# 전역 싱글톤 인스턴스
_session_service: Optional[SessionService] = None


async def get_session_service() -> Optional[SessionService]:
    """세션 서비스 인스턴스 반환 (싱글톤) - Container 의존성 제거"""
    global _session_service
    if _session_service is None:
        try:
            # ✅ Container 의존성 제거 - 직접 Repository 생성
            repository = await create_session_repository()
            _session_service = SessionService(repository)
            logger.info("✅ 세션 서비스 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 세션 서비스 초기화 실패: {e}")
            return None
    return _session_service
