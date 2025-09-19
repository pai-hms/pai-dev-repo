"""
SQL Agent 전용 LangGraph - 표준 에이전트 패턴 (다단계 추론 지원)
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
    """SQL Agent StateGraph 생성 - 표준 LangGraph 패턴 with 다단계 추론 지원"""
    
    logger.info("SQL Agent 그래프 생성 시작")
    
    # 설정 로드
    settings = await get_agent_settings()
    
    # 그래프 구성
    workflow = StateGraph(SQLAgentState)
    
    # ================== 노드 정의 ==================
    
    # 1. 프롬프트 노드
    workflow.add_node("prompt", SQLPromptNode())
    
    # 2. 에이전트 노드 (핵심 추론 엔진)
    async def agent_node(state: SQLAgentState):
        llm_service = await get_llm_service()
        sql_agent = SQLAgentNode(llm_service, AVAILABLE_TOOLS)
        return await sql_agent(state)
    
    workflow.add_node("agent", agent_node)
    
    # 3. 도구 노드 (LangGraph 표준 ToolNode)
    tool_node = ToolNode(AVAILABLE_TOOLS)
    workflow.add_node("tools", tool_node)
    
    # 4. 요약 노드 (최종 응답 직전에만 사용)
    workflow.add_node("summary", SQLSummaryNode())
    
    # 5. 응답 노드 (최종 응답 생성)
    workflow.add_node("response", SQLResponseNode())
    
    # ================== 라우팅 로직 ==================
    
    def should_continue_from_agent(state: SQLAgentState) -> Literal["tools", "summary"]:
        """✅ 에이전트에서 도구 사용 여부 판단"""
        messages = state.get("messages", [])
        if not messages:
            return "summary"  # 메시지 없으면 바로 요약으로
        
        last_message = messages[-1]
        
        # 도구 호출이 있는 경우 → tools로 이동 (다단계 추론 지원)
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🔧 도구 호출 감지: {len(last_message.tool_calls)}개 - 다단계 추론 지원")
            return "tools"
        
        # 도구 호출이 없는 경우 → summary로 이동 (최종 응답 준비)
        logger.info("💬 도구 호출 없음 - 최종 응답 준비")
        return "summary"
    
    def should_continue_from_tools(state: SQLAgentState) -> Literal["agent"]:
        """✅ 도구 실행 후 항상 agent로 돌아가기 (다단계 추론 핵심)"""
        logger.info("🔄 도구 실행 완료 - 에이전트로 돌아가서 추가 추론")
        return "agent"
    
    # ================== 엣지 설정 ==================
    
    # 시작 플로우
    workflow.add_edge(START, "prompt")
    workflow.add_edge("prompt", "agent")
    
    # ✅ 표준 LangGraph 패턴: 에이전트가 도구 필요성 판단
    workflow.add_conditional_edges(
        "agent",
        should_continue_from_agent,
        {
            "tools": "tools",
            "summary": "summary"  # 도구 불필요 시 바로 요약으로
        }
    )
    
    # ✅ 핵심 개선: 도구 실행 후 다시 에이전트로 (다단계 추론 지원)
    workflow.add_conditional_edges(
        "tools",
        should_continue_from_tools,
        {
            "agent": "agent"  # 항상 에이전트로 돌아가서 추가 추론
        }
    )
    
    # 최종 단계: 요약 → 응답 → 종료
    workflow.add_edge("summary", "response")
    workflow.add_edge("response", END)
    
    # ================== 메모리 설정 ==================
    checkpointer = None
    try:
        if settings.enable_memory and settings.postgres_url:
            # ✅ LangGraph 가이드에 따른 PostgreSQL 연결 풀 설정
            pool = AsyncConnectionPool(
                conninfo=settings.postgres_url,
                max_size=10,
                check=AsyncConnectionPool.check_connection
            )
            checkpointer = AsyncPostgresSaver(pool)
            
            # ✅ setup() 시 인덱스 생성 오류 방지
            try:
                await checkpointer.setup()
                logger.info("✅ PostgreSQL 메모리 활성화")
            except Exception as setup_error:
                error_msg = str(setup_error).lower()
                if ("transaction block" in error_msg or 
                    "concurrently" in error_msg or
                    "already exists" in error_msg or
                    "index" in error_msg):
                    logger.warning("⚠️ PostgresSaver 인덱스 생성 건너뜀 (기존 테이블 사용)")
                    # 인덱스 오류는 무시하고 checkpointer 사용
                else:
                    logger.error(f"PostgresSaver setup 실패: {setup_error}")
                    raise setup_error
        else:
            logger.info("⚠️ 메모리 비활성화 (메모리 없이 실행)")
    except Exception as e:
        logger.warning(f"메모리 설정 실패 (메모리 없이 계속): {e}")
        checkpointer = None
    
    # ================== 그래프 컴파일 ==================
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("✅ SQL Agent 그래프 생성 완료 (다단계 추론 지원)")
    logger.info(f"   - 메모리: {'✅ PostgreSQL' if checkpointer else '❌ 비활성화'}")
    logger.info(f"   - 사용 가능한 도구: {len(AVAILABLE_TOOLS)}개")
    logger.info(f"   - 다단계 추론: ✅ agent ↔ tools 루프 지원")
    
    return graph