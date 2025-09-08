# rag-server/src/chatbot/repository.py
from typing import Dict
from .domains import ChatbotConfig

class ChatbotConfigRepository:
    """챗봇 설정 저장소 - 설정 전담"""
    
    def __init__(self):
        self._configs: Dict[str, ChatbotConfig] = {}
        self._init_default_config()
    
    def _init_default_config(self):
        """기본 설정 초기화"""
        default_config = ChatbotConfig.default()
        self._configs["default"] = default_config
    
    def get_config(self, chatbot_id: str) -> ChatbotConfig:
        """설정 조회"""
        return self._configs.get(chatbot_id, self._configs["default"])
    
    def save_config(self, chatbot_id: str, config: ChatbotConfig) -> None:
        """설정 저장"""
        self._configs[chatbot_id] = config
    
    def update_config(self, chatbot_id: str, config_data: dict) -> ChatbotConfig:
        """설정 업데이트"""
        config = self.get_config(chatbot_id)
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save_config(chatbot_id, config)
        return config