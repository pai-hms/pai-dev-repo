# rag-server/src/agent/nodes.py
from langchain_core.messages import ToolMessage
from .state import AgentState
from .service import AgentService
from typing import List

class AgentNodes:
    """Agent 노드들"""
    
    def __init__(self, agent_service: AgentService):
        """AgentService를 의존성 주입으로 받음"""
        self._agent_service = agent_service
        self._tools = agent_service.get_tools()
    
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
    
    def agent_node(self, state: AgentState) -> dict:
        """Agent 실행 노드"""
        result = self._agent_service.process_state(state)
        return {"messages": [result]}