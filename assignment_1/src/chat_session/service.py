# src/chat_session/service.py
from typing import Dict, Optional
from datetime import datetime
from .entities import ChatSession

class ChatSessionService:
    """채팅 세션 비즈니스 서비스"""
    
    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
    
    async def get_or_create_session(self, thread_id: str) -> ChatSession:
        """세션 조회 또는 생성"""
        if thread_id not in self._sessions:
            self._sessions[thread_id] = ChatSession(
                thread_id=thread_id,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
        else:
            self._sessions[thread_id].last_accessed = datetime.now()
        
        return self._sessions[thread_id]
    
    async def get_session_info(self, thread_id: str) -> Optional[dict]:
        """세션 정보 조회"""
        if thread_id in self._sessions:
            session = self._sessions[thread_id]
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
        if thread_id in self._sessions:
            del self._sessions[thread_id]
            return True
        return False

    def get_all_sessions(self) -> Dict[str, ChatSession]:
        """모든 세션 조회"""
        return self._sessions
