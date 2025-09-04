# rag-server/src/agent/service.py
from typing import List
from .state import AgentState
from ..llm.service import LLMService

class AgentService:
    """에이전트 비즈니스 서비스"""
    
    def __init__(self, llm_service: LLMService, tools: List):
        """완전한 의존성 주입"""
        self._llm_service = llm_service
        self._tools = tools
        self._llm_with_tools = None  # 지연 초기화로 비동기 문제 방지
    
    def _get_llm_with_tools(self):
        """LLM with tools 지연 초기화"""
        if self._llm_with_tools is None:
            self._llm_with_tools = self._llm_service.get_llm_with_tools(self._tools)
        return self._llm_with_tools
    
    def process_state(self, state: AgentState):
        """상태 처리"""
        messages = state["messages"]
        prepared_messages = self._llm_service.prepare_messages(messages)
        llm_with_tools = self._get_llm_with_tools()
        return llm_with_tools.invoke(prepared_messages)
    
    def get_tools(self):
        """도구 목록 반환"""
        return self._tools