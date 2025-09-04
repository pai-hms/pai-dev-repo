# rag-server/src/agent/graph.py
from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import AgentNodes
from .service import AgentService

class AgentGraphFactory:
    """Agent Graph 팩토리 - DI 적용"""
    
    def __init__(self, agent_service: AgentService):
        """AgentService 의존성 주입"""
        self._agent_service = agent_service
        self._agent_nodes = AgentNodes(agent_service)  # AgentService 전체 주입
        self._executor = None
    
    def create_executor(self):
        """Executor 생성"""
        if self._executor is None:
            workflow = StateGraph(AgentState)
            
            def should_continue(state: AgentState):
                return "tools" if state["messages"][-1].tool_calls else END
            
            # 그래프 구성 
            workflow.add_node("agent", self._agent_nodes.agent_node)
            workflow.add_node("tools", self._agent_nodes.tool_node)
            workflow.set_entry_point("agent")
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
            
            self._executor = workflow.compile(checkpointer=InMemorySaver())
        
        return self._executor