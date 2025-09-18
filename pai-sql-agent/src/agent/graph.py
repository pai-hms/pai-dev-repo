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

logger = logging.getLogger(__name__)


def create_checkpointer(settings: AgentSettings) -> Optional[AsyncPostgresSaver]:
    """PostgreSQL checkpointer 생성"""
    if not settings.enable_checkpointer:
        return None
    
    try:
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://")
        
        pool = AsyncConnectionPool(db_url, min_size=1, max_size=10)
        return AsyncPostgresSaver(pool)
    except Exception as e:
        logger.error(f"Checkpointer 생성 실패: {e}")
        return None


def create_sql_agent_workflow() -> StateGraph:
    """SQL Agent 워크플로우 생성"""
    
    # 노드들 생성
    prompt_node = SQLPromptNode()
    summary_node = SQLSummaryNode()
    response_node = SQLResponseNode()  # 새로 추가
    tool_node = ToolNode(AVAILABLE_TOOLS)
    
    # 에이전트 노드
    async def agent_node(state: SQLAgentState):
        from .container import get_container
        container = await get_container()
        llm_service = await container.llm_service()
        
        sql_agent = SQLAgentNode(llm_service, AVAILABLE_TOOLS)
        return await sql_agent(state)
    
    # 개선된 라우팅 로직
    def should_continue_after_tools(state: SQLAgentState) -> Literal["agent", "summary"]:
        """도구 실행 후 다음 단계 결정"""
        messages = state.get("messages", [])
        
        # 마지막 도구 메시지 확인
        for message in reversed(messages):
            if hasattr(message, 'type') and message.type == "tool":
                # 오류가 있으면 재시도
                if message.content.startswith("Error"):
                    logger.info("도구 실행 오류 감지 - Agent로 재시도")
                    return "agent"
                # 성공하면 요약으로
                else:
                    logger.info("도구 실행 성공 - Summary로 이동")
                    return "summary"
                break
        
        # 기본적으로 요약으로
        return "summary"
    
    def should_continue_after_summary(state: SQLAgentState) -> Literal["response", "__end__"]:
        """요약 후 응답 생성 여부 결정"""
        # SQL과 데이터가 있으면 응답 생성
        if state.get("sql_query") or state.get("data"):
            logger.info("데이터 존재 - Response 생성")
            return "response"
        else:
            logger.info("데이터 없음 - 종료")
            return "__end__"
    
    # 워크플로우 구성
    workflow = StateGraph(SQLAgentState)
    
    workflow.add_node("prompt", prompt_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("summary", summary_node)
    workflow.add_node("response", response_node)  # 응답 생성 노드 추가
    
    # 엣지 구성 - 개선된 플로우
    workflow.add_edge(START, "prompt")
    workflow.add_edge("prompt", "agent")
    workflow.add_edge("agent", "tools")
    workflow.add_conditional_edges("tools", should_continue_after_tools)
    workflow.add_conditional_edges("summary", should_continue_after_summary)
    workflow.add_edge("response", END)
    
    return workflow


async def create_sql_agent_graph() -> CompiledStateGraph:
    """SQL Agent 그래프 생성"""
    try:
        settings = await get_agent_settings()
        workflow = create_sql_agent_workflow()
        checkpointer = create_checkpointer(settings)
        
        compiled_graph = workflow.compile(checkpointer=checkpointer)
        logger.info("SQL Agent 그래프 생성 완료")
        
        return compiled_graph
    except Exception as e:
        logger.error(f"SQL Agent 그래프 생성 실패: {e}")
        raise