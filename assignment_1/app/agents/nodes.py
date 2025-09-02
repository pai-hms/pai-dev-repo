# app/agents/nodes.py
from langchain_core.messages import ToolMessage
from .state import AgentState
from .tools import stock_tools

# 도구를 실행하고 그 결과를 state에 추가하는 노드
async def tool_node(state: AgentState) -> dict:
    # 마지막 메시지에 담긴 tool_calls를 확인
    last_message = state["messages"][-1]
    
    # 각 tool_call을 실행
    tool_calls = last_message.tool_calls
    tool_outputs = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        # 일치하는 도구를 찾아 실행
        for tool in stock_tools:
            if tool.name == tool_name:
                # 비동기 함수이므로 await 사용
                result = await tool.ainvoke(tool_call["args"])
                tool_outputs.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
                break
    
    return {"messages": tool_outputs}

# LLM을 호출하여 다음에 할 일을 결정하는 노드
def agent_node(state: AgentState, agent):
    result = agent(state)
    return {"messages": [result]}