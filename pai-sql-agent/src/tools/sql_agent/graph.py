"""
SQL Agent LangGraph 그래프
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import ToolMessage

# ModelExecutionService, TokenUsageService 대신 사용
from src.llm.service import LLMService, get_llm_service
from src.agent.settings import AgentSettings

from .nodes import (
    QueryGenerationAgentNode,
    QueryGenerationPromptNode,
    QuerySummaryNode,
    SQLAgentOverallState,
)
from .tools import SQLExecutionToolKit


async def create_sql_agent(
    settings: AgentSettings,
) -> CompiledStateGraph:
    """
    SQL Agent 그래프 생성
    
    플로우:
    START → query_generation_prompt → query_generation_agent → tools → 
    (오류 시 재시도) → query_summarization → END
    """
    
    # 노드 인스턴스 생성
    prompt_node = QueryGenerationPromptNode()
    summary_node = QuerySummaryNode()
    toolkit = SQLExecutionToolKit()
    tools = toolkit.get_tools()
    
    agent_node = QueryGenerationAgentNode(
        execution_service=execution_service,
        token_usage_service=token_usage_service,
        tools=tools
    )
    
    # 그래프 생성
    graph = StateGraph(SQLAgentOverallState)
    
    # 노드 추가
    graph.add_node("query_generation_prompt", prompt_node)
    graph.add_node("query_generation_agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("query_summarization", summary_node)
    
    # 조건부 엣지를 위한 함수
    def retry_if_error_exists(state: SQLAgentOverallState) -> Literal["query_generation_agent", "query_summarization"]:
        """오류가 있으면 재시도, 없으면 요약으로 진행"""
        for message in reversed(state["messages"]):
            if isinstance(message, ToolMessage) and message.content.startswith("Error"):
                return "query_generation_agent"
            else:
                break
        return "query_summarization"
    
    # 엣지 연결
    graph.add_edge(START, "query_generation_prompt")
    graph.add_edge("query_generation_prompt", "query_generation_agent")
    graph.add_edge("query_generation_agent", "tools")
    graph.add_conditional_edges("tools", retry_if_error_exists)
    graph.add_edge("query_summarization", END)
    
    # 컴파일 (SQL Agent는 체크포인터 없이 단순 실행)
    return graph.compile(checkpointer=None)
