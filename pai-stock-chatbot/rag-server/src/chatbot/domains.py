# rag-server/src/chatbot/domains.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class ChatbotConfig:
    """챗봇 설정 정보"""
    model_name: str
    temperature: float
    max_tokens: int
    system_prompt: str
    tools_enabled: bool = True

@dataclass
class ChatSession:
    """채팅 세션 도메인 객체"""
    thread_id: str
    created_at: datetime
    last_accessed: datetime
    message_count: int = 0
    config: Optional[ChatbotConfig] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def increment_message_count(self):
        """메시지 카운트 증가"""
        self.message_count += 1
        self.last_accessed = datetime.now()

@dataclass
class ChatMessage:
    """채팅 메시지 도메인 객체"""
    content: str
    role: str  # 'user', 'assistant', 'system'
    timestamp: datetime
    thread_id: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}