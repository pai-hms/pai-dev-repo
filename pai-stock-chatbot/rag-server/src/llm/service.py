# rag-server/src/llm/service.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from .settings import LLMSettings

class LLMService:
    """LLM 비즈니스 서비스"""
    
    def __init__(self, settings: LLMSettings = None):
        from .settings import settings as default_settings
        self._settings = settings or default_settings
        self._llm = None
    
    def get_llm_with_tools(self, tools):
        """도구 바인딩된 LLM 반환"""
        if self._llm is None:
            if not self._settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            
            self._llm = ChatOpenAI(
                model=self._settings.OPENAI_MODEL,
                temperature=self._settings.OPENAI_TEMPERATURE,
                api_key=self._settings.OPENAI_API_KEY
            )
        
        return self._llm.bind_tools(tools)
    
    def prepare_messages(self, messages):
        """시스템 메시지 추가"""
        system_msg = SystemMessage(content=self._settings.SYSTEM_PROMPT)
        return [system_msg] + messages

# 싱글톤 제거 - DI Container에서 관리
# llm_service = LLMService()  # 제거