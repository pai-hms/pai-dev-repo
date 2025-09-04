# rag-server/src/chat_session/service.py
from typing import Optional
from datetime import datetime
from .entities import ChatSession
from .repository import ChatSessionRepository

class ChatSessionService:
    """채팅 세션 비즈니스 서비스"""
    
    def __init__(self, repository: ChatSessionRepository = None):
        self._repository = repository or ChatSessionRepository()
    
    async def get_or_create_session(self, thread_id: str) -> ChatSession:
        """세션 조회 또는 생성"""
        session = self._repository.find_by_id(thread_id)
        if session is None:
            session = ChatSession(
                thread_id=thread_id,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            self._repository.save(session)
        else:
            session.last_accessed = datetime.now()
            self._repository.save(session)
        
        return session
    
    async def get_session_info(self, thread_id: str) -> Optional[dict]:
        """세션 정보 조회"""
        session = self._repository.find_by_id(thread_id)
        if session:
            return {
                'thread_id': thread_id,
                'created_at': session.created_at.isoformat(),
                'last_accessed': session.last_accessed.isoformat(),
                'message_count': session.message_count,
                'active': True
            }
        return None
    
    async def close_session(self, thread_id: str) -> bool:
        """세션 종료"""
        return self._repository.delete(thread_id)

    def get_all_sessions(self):
        """모든 세션 조회"""
        return self._repository.find_all()
