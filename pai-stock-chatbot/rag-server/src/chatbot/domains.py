# rag-server/src/chatbot/domains.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ChatbotConfig:
    """챗봇 설정 정보"""
    chatbot_id: str
    model_name: str
    temperature: float
    max_tokens: int
    system_prompt: str
    tools_enabled: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @staticmethod
    def default() -> "ChatbotConfig":
        """기본 챗봇 설정"""
        return ChatbotConfig(
            chatbot_id="default",
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000,
            system_prompt="당신은 주식 정보를 도와주는 AI 어시스턴트입니다."
        )