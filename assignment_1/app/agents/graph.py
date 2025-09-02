# app/agents/graph.py
from functools import partial
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import agent_node, tool_node
from .tools import stock_tools
from ..core.config import settings

# LLM과 도구를 바인딩하여 Agent 생성
def create_agent():
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.OPENAI_API_KEY)
    
    messages = [
        SystemMessage(
            content="You are a helpful stock assistant. "
            "You can use tools to get current stock prices and perform calculations. "
            "Respond in Korean."
        )
    ]
    
    agent = llm.bind_tools(stock_tools)
    
    return lambda state: agent.invoke(messages + state["messages"])

# 조건부 엣지
def should_continue(state: AgentState):
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

# 그래프를 생성하고 메모리를 적용하여 컴파일하는 함수
def create_memory_agent_executor():
    agent = create_agent()
    
    memory = InMemorySaver()
    
    workflow = StateGraph(AgentState)
    
    bound_agent_node = partial(agent_node, agent=agent)

    workflow.add_node("agent", bound_agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(checkpointer=memory)

# 컴파일된 실행기(executor)를 전역 변수로 생성
agent_executor = create_memory_agent_executor()