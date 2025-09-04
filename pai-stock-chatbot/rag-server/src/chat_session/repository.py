# rag-server/src/chat_session/repository.py
from typing import Dict, Optional
from .entities import ChatSession

class ChatSessionRepository:
    """채팅 세션 데이터 저장소 - 데이터 주권 담당"""
    
    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
    
    def save(self, session: ChatSession) -> None:
        """세션 저장"""
        self._sessions[session.thread_id] = session
    
    def find_by_id(self, thread_id: str) -> Optional[ChatSession]:
        """ID로 세션 조회"""
        return self._sessions.get(thread_id)
    
    def delete(self, thread_id: str) -> bool:
        """세션 삭제"""
        if thread_id in self._sessions:
            del self._sessions[thread_id]
            return True
        return False
    
    def find_all(self) -> Dict[str, ChatSession]:
        """모든 세션 조회"""
        return self._sessions.copy()  # 불변성 보장