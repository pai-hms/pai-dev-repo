# rag-server/src/agent/service.py
from typing import List
from .state import AgentState
from .tools import get_agent_tools  # Stock tools 통합
from ..llm.service import LLMService

class AgentService:
    """에이전트 비즈니스 서비스"""
    
    def __init__(self, llm_service: LLMService):
        """간소화된 의존성 주입"""
        self._llm_service = llm_service
        self._tools = get_agent_tools()  # 직접 로드
        self._llm_with_tools = None
    
    def _get_llm_with_tools(self):
        """LLM with tools 지연 초기화"""
        if self._llm_with_tools is None:
            self._llm_with_tools = self._llm_service.get_llm_with_tools(self._tools)
        return self._llm_with_tools
    
    def _get_streaming_llm_with_tools(self):
        """스트리밍용 LLM with tools 지연 초기화"""
        return self._llm_service.get_streaming_llm_with_tools(self._tools)
    
    def process_state(self, state: AgentState):
        """상태 처리"""
        messages = state["messages"]
        prepared_messages = self._llm_service.prepare_messages(messages)
        llm_with_tools = self._get_llm_with_tools()
        return llm_with_tools.invoke(prepared_messages)
    
    async def process_state_streaming(self, state: AgentState):
        """스트리밍 상태 처리"""
        messages = state["messages"]
        prepared_messages = self._llm_service.prepare_messages(messages)
        llm_with_tools = self._get_streaming_llm_with_tools()
        
        # 스트리밍으로 응답 생성
        async for chunk in llm_with_tools.astream(prepared_messages):
            yield chunk
    
    def get_tools(self):
        """도구 목록 반환"""
        return self._tools