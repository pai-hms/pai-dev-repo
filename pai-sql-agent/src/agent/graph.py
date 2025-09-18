"""
LangGraph 표준 패턴 SQL Agent 그래프
Agent → Tools → Agent → Finalize 워크플로우
"""
import logging
from typing import Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import ToolNode, tools_condition
from psycopg_pool import AsyncConnectionPool

from .nodes import LangAgentNode, LangGraphAgentState
from .settings import AgentSettings, get_agent_settings
from .tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


# 전역 체크포인터 인스턴스 (연결 유지용)
_global_checkpointer: Optional[AsyncPostgresSaver] = None


def create_checkpointer(settings: AgentSettings) -> Optional[AsyncPostgresSaver]:
    """
    PostgreSQL checkpointer 생성 (LangGraph 표준)
    
    Args:
        settings: Agent 설정 (pydantic_settings 기반)
        
    Returns:
        AsyncPostgresSaver 또는 None (설정 실패시)
    """
    if not settings.enable_checkpointer:
        logger.info("체크포인터가 비활성화되어 있습니다")
        return None
    
    try:
        # DATABASE_URL에서 postgresql:// 형식 확인 및 변환
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://")
        elif not db_url.startswith("postgresql://"):
            db_url = f"postgresql://{db_url}"
            
        # AsyncConnectionPool 생성 (LangGraph 표준 방식)
        pool = AsyncConnectionPool(
            db_url,
            min_size=1,
            max_size=10,
        )
        
        # AsyncPostgresSaver 생성
        checkpointer = AsyncPostgresSaver(pool)
        logger.info("✅ PostgreSQL checkpointer 생성 완료")
        
        return checkpointer
        
    except Exception as e:
        logger.error(f"❌ Checkpointer 생성 실패: {e}")
        logger.warning("🔄 체크포인터 비활성화 - 멀티턴 대화 기능 사용 불가")
        return None


async def cleanup_checkpointer():
    """
    체크포인터 정리 (애플리케이션 종료시 호출)
    ConnectionPool을 사용하므로 별도 정리 불필요
    """
    logger.info("🧹 체크포인터 정리 완료 (ConnectionPool 자동 관리)")


def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    """현재 활성 체크포인터 반환 (없으면 None)"""
    return _global_checkpointer


def create_lang_agent(
    settings: AgentSettings,
    execution_service: Any,
    token_usage_service: Any,
    prompt_generator: Any,
    tools: Optional[List[Any]] = None,
    **tool_kwargs
) -> CompiledStateGraph:
    """
    LangGraph Agent 생성 (표준 패턴)
    
    Args:
        settings: Agent 설정
        execution_service: 모델 실행 서비스
        token_usage_service: 토큰 사용량 서비스
        prompt_generator: 프롬프트 생성기
        tools: 사용할 도구 목록 (선택사항)
        **tool_kwargs: 개별 도구 설정
    
    Returns:
        CompiledStateGraph: 컴파일된 LangGraph
    """
    
    # 도구 설정 (기본값 또는 전달받은 도구 사용)
    if tools is None:
        tools = AVAILABLE_TOOLS
    
    # 노드 생성
    agent_node = LangAgentNode(
        execution_service=execution_service,
        tools={tool.name: tool for tool in tools} if tools else {},
        prompt_generator=prompt_generator,
        token_usage_service=token_usage_service,
    )
    
    tool_node = ToolNode(tools) if tools else None
    
    # 그래프 생성 (LangGraph 표준 패턴)
    workflow = StateGraph(LangGraphAgentState)
    
    # 노드 추가
    workflow.add_node("agent", agent_node)
    if tool_node:
        workflow.add_node("tools", tool_node)
    
    # 엣지 설정
    workflow.set_entry_point("agent")
    
    if tool_node:
        # 표준 도구 조건부 라우팅
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")
    
    # 체크포인터 설정
    checkpointer = create_checkpointer(settings)
    
    # 컴파일
    compiled_graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("✅ LangGraph Agent 생성 완료")
    logger.info(f"🔄 워크플로우: Agent → {'Tools → Agent' if tool_node else 'END'}")
    
    return compiled_graph


async def create_sql_agent_graph() -> CompiledStateGraph:
    """
    하위 호환성을 위한 SQL Agent 그래프 생성 함수
    """
    settings = await get_agent_settings()
    
    # 기본 설정으로 에이전트 생성 (실제 서비스들은 None으로 설정)
    return create_lang_agent(
        settings=settings,
        execution_service=None,  # 실제 구현에서는 DI Container에서 주입
        token_usage_service=None,  # 실제 구현에서는 DI Container에서 주입
        prompt_generator=None,  # 실제 구현에서는 DI Container에서 주입
        tools=AVAILABLE_TOOLS
    )