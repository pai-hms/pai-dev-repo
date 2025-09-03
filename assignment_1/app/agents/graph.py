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
from typing import List

def prepare_messages(state: AgentState) -> List:
    """메시지 준비"""
    messages = state["messages"]
    system_msg = SystemMessage(content="당신은 주가 계산을 도와주는 AI Agent입니다.")
    return [system_msg] + messages

def create_agent():
    """간소화된 에이전트 생성"""
    llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14", 
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY
    ).bind_tools(stock_tools)
    
    def agent_wrapper(state: AgentState):
        messages = prepare_messages(state)
        return llm.invoke(messages)
    
    return agent_wrapper

def should_continue(state: AgentState):
    """도구 호출 여부를 결정하는 조건부 엣지"""
    return "tools" if state["messages"][-1].tool_calls else END

def create_memory_agent_executor():
    """세션별 독립적인 메모리를 가진 에이전트 실행기 생성"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", partial(agent_node, agent=create_agent()))
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(checkpointer=InMemorySaver())