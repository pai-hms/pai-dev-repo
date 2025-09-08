# rag-server/src/agent/graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import ToolMessage
from .state import AgentState
from .service import AgentService

class AgentGraphFactory:
    """Agent Graph 팩토리 - DI 적용"""
    
    def __init__(self, agent_service: AgentService):
        """AgentService 의존성 주입"""
        self._agent_service = agent_service
        self._tools = agent_service.get_tools()
        self._executor = None
    
    def agent_node(self, state: AgentState) -> dict:
        """Agent 실행 노드"""
        result = self._agent_service.process_state(state)
        return {"messages": [result]}
    
    async def streaming_agent_node(self, state: AgentState):
        """스트리밍 Agent 실행 노드"""
        messages = []
        async for chunk in self._agent_service.process_state_streaming(state):
            messages.append(chunk)
            yield {"messages": [chunk]}
        
        # 최종 상태 반환
        return {"messages": messages}
    
    async def tool_node(self, state: AgentState) -> dict:
        """도구 실행 노드"""
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        tool_outputs = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            for tool in self._tools:
                if tool.name == tool_name:
                    result = await tool.ainvoke(tool_call["args"])
                    tool_outputs.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )
                    break
        
        return {"messages": tool_outputs}
    
    def create_executor(self):
        """Executor 생성"""
        if self._executor is None:
            workflow = StateGraph(AgentState)
            
            def should_continue(state: AgentState):
                return "tools" if state["messages"][-1].tool_calls else END
            
            # 그래프 구성 
            workflow.add_node("agent", self.agent_node)
            workflow.add_node("tools", self.tool_node)
            workflow.set_entry_point("agent")
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
            
            self._executor = workflow.compile(checkpointer=InMemorySaver())
        
        return self._executor