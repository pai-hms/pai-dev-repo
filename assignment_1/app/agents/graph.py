# app/agents/graph.py
from functools import partial
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import AgentState
from .nodes import agent_node, tool_node
from .tools import stock_tools
from ..core.config import settings

# LLM과 도구를 바인딩하여 Agent 생성 - Chain 사용
def create_agent():
    # LLM 생성
    llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14", 
        # temperature=0, 
        api_key=settings.OPENAI_API_KEY
    )
    
    # 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 주가 계산을 도와주는 AI Agent입니다."),
        ("placeholder", "{messages}")  # 메시지 히스토리
    ])
    
    # Chain 생성 
    chain = prompt | llm.bind_tools(stock_tools)
    
    # agent_node에서 사용할 수 있도록 래핑
    def agent_wrapper(state: AgentState):
        # 메시지 히스토리를 프롬프트에 맞게 변환
        messages = state["messages"]
        result = chain.invoke({"messages": messages})
        return result
    
    return agent_wrapper

# 조건부 엣지
def should_continue(state: AgentState):
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

# 그래프를 생성하고 메모리를 적용하여 컴파일하는 함수
def create_memory_agent_executor():
    agent = create_agent()
    
    memory = InMemorySaver()
    
    workflow = StateGraph(AgentState) # SateGraph 생성
    
    # 노드 추가
    bound_agent_node = partial(agent_node, agent=agent)
    workflow.add_node("agent", bound_agent_node)
    workflow.add_node("tools", tool_node)
    
    # 엣지 설정
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    # 컴파일
    return workflow.compile(checkpointer=memory)

# 컴파일된 실행기(executor)를 전역 변수로 생성
agent_executor = create_memory_agent_executor()