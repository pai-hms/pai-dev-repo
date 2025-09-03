# src/agent/service.py
from typing import List
from .state import AgentState
from ..llm.service import LLMService

class AgentService:
    """에이전트 비즈니스 서비스"""
    
    def __init__(self, llm_service: LLMService, tools: List):
        self._llm_service = llm_service
        self._tools = tools
        self._llm_with_tools = llm_service.get_llm_with_tools(tools)
    
    def process_state(self, state: AgentState):
        """상태 처리"""
        messages = state["messages"]
        prepared_messages = self._llm_service.prepare_messages(messages)
        return self._llm_with_tools.invoke(prepared_messages)
    
    def get_tools(self):
        """도구 목록 반환"""
        return self._tools
