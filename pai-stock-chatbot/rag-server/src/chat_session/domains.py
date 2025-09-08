# rag-server/src/chat_session/domains.py
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime
import uuid

@dataclass
class ChatSession:
    """유저와 챗봇이 대화하는 채팅방"""
    session_id: str
    title: str
    chatbot_id: str  # 어떤 챗봇과 대화하는지
    created_at: datetime
    last_accessed: datetime
    message_count: int = 0
    metadata: Dict[str, Any] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @staticmethod
    def new(title: str, chatbot_id: str = "default") -> "ChatSession":
        """새 세션 생성"""
        return ChatSession(
            session_id=str(uuid.uuid4()),
            title=title,
            chatbot_id=chatbot_id,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
    
    def increment_message_count(self):
        """메시지 카운트 증가"""
        self.message_count += 1
        self.last_accessed = datetime.now()
    
    def close(self):
        """세션 종료"""
        self.is_active = False
        self.last_accessed = datetime.now()

@dataclass
class ChatMessage:
    """채팅 메시지"""
    content: str
    role: str  # 'user', 'assistant', 'system'
    timestamp: datetime
    session_id: str  # thread_id 대신 session_id 사용
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}