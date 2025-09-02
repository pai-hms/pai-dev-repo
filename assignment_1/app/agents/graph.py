# app/agents/graph.py
from functools import partial
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import agent_node, tool_node
from .tools import stock_tools
from ..core.config import settings
import threading
from typing import Dict, List
from datetime import datetime

# 스레드 로컬 저장소로 세션별 격리
_thread_local = threading.local()

def create_system_message() -> SystemMessage:
    """간단한 시스템 메시지 생성"""
    return SystemMessage(content="당신은 주가 계산을 도와주는 AI Agent입니다.")

def prepare_messages(state: AgentState) -> List:
    """메시지 준비"""
    messages = state["messages"]
    system_msg = create_system_message()
    return [system_msg] + messages

def create_agent():
    """Chain 기반으로 개선된 에이전트 생성"""
    
    # LLM 컴포넌트 생성
    llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14", 
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY
    )
    
    # 도구 바인딩된 LLM
    llm_with_tools = llm.bind_tools(stock_tools)
    
    # 메시지 준비 Runnable
    message_preparer = RunnableLambda(prepare_messages)
    
    # Chain 구성 - 파이프라인으로 연결
    chain = (
        message_preparer      # AgentState -> 준비된 메시지들
        | llm_with_tools      # 메시지들 -> AI 응답
    )
    
    # AgentState 호환을 위한 래퍼
    def agent_wrapper(state: AgentState):
        """Chain을 AgentState와 호환시키는 래퍼"""
        result = chain.invoke(state)
        return result
    
    return agent_wrapper

# 조건부 엣지
def should_continue(state: AgentState):
    """도구 호출 여부를 결정하는 조건부 엣지"""
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

def create_memory_agent_executor():
    """세션별 독립적인 메모리를 가진 에이전트 실행기 생성"""
    # Chain 기반 에이전트 사용
    agent = create_agent() 
    
    # 각 세션마다 독립적인 메모리 생성
    memory = InMemorySaver()
    
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    bound_agent_node = partial(agent_node, agent=agent)
    workflow.add_node("agent", bound_agent_node)
    workflow.add_node("tools", tool_node)
    
    # 엣지 설정
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    # 세션별 독립적인 컴파일된 실행기 반환
    return workflow.compile(checkpointer=memory)