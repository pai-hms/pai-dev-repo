# rag-server/src/chat_session/service.py
from typing import Optional, List
import logging
from datetime import datetime

from .domains import ChatSession, ChatMessage
from .repository import ChatSessionRepository
from src.exceptions import InvalidRequestException, SessionNotFoundException

logger = logging.getLogger(__name__)

class ChatSessionService:
    """채팅 세션 관리 서비스 - 대화방 관리 전담"""
    
    def __init__(self, repository: ChatSessionRepository):
        self._repository = repository
    
    # === 세션 생명주기 관리 ===
    async def start_new_session(self, title: str, chatbot_id: str = "default") -> ChatSession:
        """새 채팅 세션 시작"""
        session = ChatSession.new(title=title, chatbot_id=chatbot_id)
        self._repository.save_session(session)
        logger.info(f"New session started: {session.session_id}")
        return session
    
    async def get_session(self, session_id: str) -> ChatSession:
        """세션 조회"""
        session = self._repository.find_session_by_id(session_id)
        if not session:
            raise SessionNotFoundException(f"Session {session_id} not found")
        return session
    
    async def close_session(self, session_id: str) -> bool:
        """세션 종료"""
        session = await self.get_session(session_id)
        session.close()
        self._repository.save_session(session)
        return True
    
    async def get_active_sessions(self) -> List[ChatSession]:
        """활성 세션 목록"""
        return list(self._repository.find_active_sessions().values())
    
    # === 메시지 관리 ===
    async def save_message(self, session_id: str, content: str, role: str) -> ChatMessage:
        """메시지 저장"""
        # 세션 존재 확인
        session = await self.get_session(session_id)
        
        message = ChatMessage(
            content=content,
            role=role,
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self._repository.save_message(message)
        session.increment_message_count()
        self._repository.save_session(session)
        
        return message
    
    async def get_messages(self, session_id: str) -> List[ChatMessage]:
        """세션의 메시지 목록"""
        await self.get_session(session_id)  # 세션 존재 확인
        return self._repository.find_messages_by_session(session_id)

    async def update_session(self, session: ChatSession) -> None:
        """세션 업데이트"""
        self._repository.save_session(session)