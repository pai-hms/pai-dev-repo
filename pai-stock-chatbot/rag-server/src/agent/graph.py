# rag-server/src/agent/graph.py
from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import agent_node, tool_node
from .service import AgentService

class AgentGraphFactory:
    """Agent Graph 팩토리 - Open-Closed 원칙 적용"""
    
    def __init__(self, agent_service: AgentService):
        self._agent_service = agent_service
        self._executor = None
    
    def create_executor(self):
        """Executor 생성"""
        if self._executor is None:
            workflow = StateGraph(AgentState)
            
            def should_continue(state: AgentState):
                return "tools" if state["messages"][-1].tool_calls else END
            
            # 그래프 구성
            workflow.add_node("agent", partial(agent_node, agent_service=self._agent_service))
            workflow.add_node("tools", tool_node)
            workflow.set_entry_point("agent")
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
            
            self._executor = workflow.compile(checkpointer=InMemorySaver())
        
        return self._executor

# 하위 호환성을 위한 함수 (점진적 마이그레이션)
def get_agent_executor():
    """레거시 지원 함수"""
    from ..llm.service import LLMService
    from ..stock.tools import stock_tools
    
    # 임시로 직접 생성 (추후 DI로 교체)
    llm_service = LLMService()
    agent_service = AgentService(llm_service, stock_tools)
    factory = AgentGraphFactory(agent_service)
    return factory.create_executor()