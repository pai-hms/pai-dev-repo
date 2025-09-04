# rag-server/src/agent/graph.py
from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import agent_node, tool_node
from .service import AgentService
from ..llm.service import llm_service
from ..stock.tools import stock_tools

# Singleton 패턴
_executor_instance = None

def get_agent_executor():
    """Singleton executor 반환"""
    global _executor_instance
    if _executor_instance is None:
        workflow = StateGraph(AgentState)
        
        # 간단한 Agent 서비스
        agent_service = AgentService(llm_service, stock_tools)
        
        def should_continue(state: AgentState):
            return "tools" if state["messages"][-1].tool_calls else END
        
        # 그래프 구성
        workflow.add_node("agent", partial(agent_node, agent_service=agent_service))
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        _executor_instance = workflow.compile(checkpointer=InMemorySaver())
    
    return _executor_instance

# 하위 호환성
def create_memory_agent_executor():
    return get_agent_executor()
