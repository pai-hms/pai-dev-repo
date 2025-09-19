"""
SQL Agent 전용 LangGraph - 응답 생성 개선
"""
import logging
from typing import Optional, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import ToolNode
from psycopg_pool import AsyncConnectionPool

from .nodes import SQLAgentState, SQLPromptNode, SQLAgentNode, SQLSummaryNode, SQLResponseNode
from .settings import AgentSettings, get_agent_settings
from .tools import AVAILABLE_TOOLS
from src.llm.service import get_llm_service

logger = logging.getLogger(__name__)


async def create_sql_agent_graph() -> CompiledStateGraph:
    """SQL Agent StateGraph 생성"""
    
    logger.info("SQL Agent 그래프 생성 시작")
    
    # 설정 로드
    settings = await get_agent_settings()
    
    # 그래프 구성
    workflow = StateGraph(SQLAgentState)
    
    # ================== 노드 정의 ==================
    
    # 1. 프롬프트 노드
    workflow.add_node("prompt", SQLPromptNode())
    
    # 2. 에이전트 노드
    async def agent_node(state: SQLAgentState):
        llm_service = await get_llm_service()
        
        sql_agent = SQLAgentNode(llm_service, AVAILABLE_TOOLS)
        return await sql_agent(state)
    
    # 개선된 라우팅 로직
    def should_continue(state: SQLAgentState) -> Literal["tools", "response"]:
        """도구 사용 여부에 따른 라우팅"""
        messages = state.get("messages", [])
        if not messages:
            return "response"
        
        last_message = messages[-1]
        
        # 도구 호출이 있는 경우
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # 도구 호출이 없는 경우 바로 응답
        return "response"
    
    # 3. 도구 노드 (ToolNode 사용)
    tool_node = ToolNode(AVAILABLE_TOOLS)
    
    # 4. 요약 노드
    workflow.add_node("summary", SQLSummaryNode())
    
    # 5. 응답 노드
    workflow.add_node("response", SQLResponseNode())
    
    # ================== 노드 등록 ==================
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # ================== 엣지 설정 ==================
    
    # 시작점
    workflow.add_edge(START, "prompt")
    workflow.add_edge("prompt", "agent")
    
    # 조건부 엣지: agent -> tools 또는 response
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "response": "response"
        }
    )
    
    # 도구 실행 후 요약
    workflow.add_edge("tools", "summary")
    workflow.add_edge("summary", "response")
    
    # 응답 후 종료
    workflow.add_edge("response", END)
    
    # ================== 메모리 설정 ==================
    checkpointer = None
    try:
        if settings.enable_memory and settings.postgres_url:
            # 비동기 PostgreSQL 연결 풀 생성
            pool = AsyncConnectionPool(
                conninfo=settings.postgres_url,
                max_size=10,
                check=AsyncConnectionPool.check_connection
            )
            checkpointer = AsyncPostgresSaver(pool)
            logger.info("✅ PostgreSQL 메모리 활성화")
        else:
            logger.info("⚠️ 메모리 비활성화 (메모리 없이 실행)")
    except Exception as e:
        logger.warning(f"메모리 설정 실패 (메모리 없이 계속): {e}")
    
    # ================== 그래프 컴파일 ==================
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("SQL Agent 그래프 생성 완료")
    return graph