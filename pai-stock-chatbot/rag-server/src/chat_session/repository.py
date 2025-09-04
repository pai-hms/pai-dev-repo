# rag-server/src/chat_session/repository.py
from typing import Dict, Optional, List
from datetime import datetime
from .domains import ChatSession, ChatMessage

class ChatSessionRepository:
    """채팅 세션 데이터 저장소"""
    
    def __init__(self):
        # 세션과 메시지 데이터를 통합 관리
        self._sessions: Dict[str, ChatSession] = {}
        self._messages: Dict[str, List[ChatMessage]] = {}
    
    # === Session 관리 (데이터 주권) ===
    def save_session(self, session: ChatSession) -> None:
        """세션 저장"""
        self._sessions[session.session_id] = session
    
    def find_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        """ID로 세션 조회"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제 (관련 데이터 모두 삭제)"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            # 관련 메시지도 함께 삭제 (데이터 일관성)
            if session_id in self._messages:
                del self._messages[session_id]
            return True
        return False
    
    def find_all_sessions(self) -> Dict[str, ChatSession]:
        """모든 세션 조회"""
        return self._sessions.copy()  # 불변성 보장
    
    def find_active_sessions(self) -> Dict[str, ChatSession]:
        """활성 세션만 조회"""
        return {
            sid: session for sid, session in self._sessions.items() 
            if session.is_active
        }
    
    # === Message 관리 (데이터 주권) ===
    def save_message(self, message: ChatMessage) -> None:
        """메시지 저장"""
        if message.session_id not in self._messages:
            self._messages[message.session_id] = []
        self._messages[message.session_id].append(message)
        
        # 세션의 메시지 카운트 업데이트
        if message.session_id in self._sessions:
            self._sessions[message.session_id].increment_message_count()
    
    def find_messages_by_session(self, session_id: str) -> List[ChatMessage]:
        """세션별 메시지 조회"""
        return self._messages.get(session_id, []).copy()  # 불변성 보장
    
    def get_message_count(self, session_id: str) -> int:
        """세션별 메시지 개수"""
        return len(self._messages.get(session_id, []))