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
        default_config = ChatbotConfig(
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000,
            system_prompt="당신은 주식 정보를 도와주는 AI 어시스턴트입니다.",
            tools_enabled=True
        )
        self._configs["default"] = default_config
    
    def get_config(self, config_id: str) -> ChatbotConfig:
        """설정 조회"""
        return self._configs.get(config_id, self._configs["default"])
    
    def save_config(self, config_id: str, config: ChatbotConfig) -> None:
        """설정 저장"""
        self._configs[config_id] = config
    
    def update_config(self, config_id: str, config_data: dict) -> ChatbotConfig:
        """설정 업데이트"""
        config = self.get_config(config_id)
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save_config(config_id, config)
        return config