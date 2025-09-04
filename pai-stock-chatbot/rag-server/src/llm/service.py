# rag-server/src/llm/service.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from .settings import settings

class LLMService:
    """LLM 비즈니스 서비스"""
    
    def __init__(self):
        self._llm = None
    
    def get_llm_with_tools(self, tools):
        """도구 바인딩된 LLM 반환"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            
            self._llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY
            )
        
        return self._llm.bind_tools(tools)
    
    def prepare_messages(self, messages):
        """시스템 메시지 추가"""
        system_msg = SystemMessage(content=settings.SYSTEM_PROMPT)
        return [system_msg] + messages

# 싱글톤
llm_service = LLMService()
