# rag-server/src/chat_session/service.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from .domains import ChatSession, ChatMessage
from .repository import ChatSessionRepository

class ChatSessionService:
    """채팅 세션 비즈니스 서비스 - 세션 관리 전담"""
    
    def __init__(self, repository: ChatSessionRepository):
        """완전한 의존성 주입"""
        self._repository = repository
    
    # === Session 생명주기 관리 ===
    async def get_or_create_session(self, thread_id: str, config_id: str = "default") -> ChatSession:
        """세션 조회 또는 생성"""
        session = self._repository.find_session_by_id(thread_id)
        
        if session is None:
            session = ChatSession(
                thread_id=thread_id,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                config_id=config_id
            )
            self._repository.save_session(session)
        else:
            session.last_accessed = datetime.now()
            self._repository.save_session(session)
        
        return session
    
    async def close_session(self, thread_id: str) -> bool:
        """세션 종료"""
        session = self._repository.find_session_by_id(thread_id)
        if session:
            session.close()
            self._repository.save_session(session)
            return True
        return False
    
    async def delete_session(self, thread_id: str) -> bool:
        """세션 완전 삭제"""
        return self._repository.delete_session(thread_id)
    
    # === Session 정보 조회 ===
    async def get_session_info(self, thread_id: str) -> Optional[Dict]:
        """세션 정보 조회"""
        session = self._repository.find_session_by_id(thread_id)
        if session:
            message_count = self._repository.get_message_count(thread_id)
            return {
                "thread_id": session.thread_id,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "message_count": message_count,
                "config_id": session.config_id,
                "is_active": session.is_active,
                "metadata": session.metadata
            }
        return None
    
    async def get_all_active_sessions(self) -> List[Dict]:
        """활성 세션 목록"""
        sessions = self._repository.find_active_sessions()
        result = []
        for session in sessions.values():
            message_count = self._repository.get_message_count(session.thread_id)
            result.append({
                "thread_id": session.thread_id,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "message_count": message_count,
                "is_active": session.is_active
            })
        return result
    
    # === Message 관리 ===
    async def save_message(self, thread_id: str, content: str, role: str) -> ChatMessage:
        """메시지 저장"""
        message = ChatMessage(
            thread_id=thread_id,
            content=content,
            role=role,
            timestamp=datetime.now()
        )
        self._repository.save_message(message)
        return message
    
    async def get_messages(self, thread_id: str) -> List[ChatMessage]:
        """스레드별 메시지 조회"""
        return self._repository.find_messages_by_thread(thread_id)