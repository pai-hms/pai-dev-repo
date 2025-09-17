"""
단일 SQL Agent 그래프
"""
import logging
from langgraph.graph import StateGraph, START, END

from .nodes import (
    AgentState,
    analyze_question_node,
    generate_sql_node,
    execute_sql_node,
    generate_response_node
)

logger = logging.getLogger(__name__)


async def create_sql_agent_graph() -> StateGraph:
    """
    단일 SQL Agent 그래프 생성
    
    워크플로우:
    START → analyze → generate_sql → execute_sql → generate_response → END
    
    선형적이고 단순한 흐름
    """
    
    # 그래프 생성
    workflow = StateGraph(AgentState)
    
    # 노드 추가 (최소한의 노드만)
    workflow.add_node("analyze", analyze_question_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # 완전 선형 흐름 (조건부 없음)
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # 컴파일
    graph = workflow.compile()
    
    logger.info("✅ 단일 SQL Agent 그래프 생성 완료")
    return graph