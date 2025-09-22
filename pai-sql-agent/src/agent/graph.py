"""
SQL Agent 전용 LangGraph
"""
import logging
from typing import Optional, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langchain_core.messages import SystemMessage

from .nodes import SQLAgentState, SQLPromptNode, SQLAgentNode, SQLSummaryNode, SQLResponseNode
from .settings import AgentSettings, get_agent_settings
from .tools import AVAILABLE_TOOLS
from src.llm.service import get_llm_service
from src.agent.prompt import DATABASE_SCHEMA_INFO

logger = logging.getLogger(__name__)


async def create_sql_agent_graph() -> CompiledStateGraph:
    """SQL Agent StateGraph 생성"""
    
    logger.info("SQL Agent 그래프 생성 시작")
    
    # 설정 로드
    logger.info("Agent 설정 로드 시작")
    settings = await get_agent_settings()
    logger.info("Agent 설정 로드 완료")
    
    # 그래프 구성
    workflow = StateGraph(SQLAgentState)
    
    # ================== 노드 정의 ==================
    
    # 1. 에이전트 노드 (핵심 추론 엔진) - 시스템 프롬프트 포함
    async def agent_node(state: SQLAgentState):
        logger.info("에이전트 노드 실행 시작")
        logger.info(f"현재 메시지 수: {len(state.get('messages', []))}")
        
        # 시스템 프롬프트 자동 추가
        if not state.get("messages") or not any(
            msg.__class__.__name__ == "SystemMessage" for msg in state["messages"]
        ):
            logger.info("시스템 프롬프트 추가")
            system_prompt = f"""당신은 데이터 전문 SQL 분석가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

**응답 가이드라인:**
1. 데이터 관련 질문: SQL 쿼리를 생성하고 sql_db_query 도구로 실행
2. 인사말/간단한 질문: 친근하게 응답하고 도움이 필요한 경우 제안
3. 모든 응답은 한국어로 작성

이전 대화 맥락을 고려하여 연속적인 대화를 지원해주세요."""
            
            messages = [SystemMessage(content=system_prompt)] + state.get("messages", [])
            state = {**state, "messages": messages}
        
        try:
            logger.info("LLM 서비스 가져오기")
            llm_service = await get_llm_service()
            logger.info("LLM 서비스 가져오기 완료")
            
            logger.info("SQL Agent 노드 생성")
            sql_agent = SQLAgentNode(llm_service, AVAILABLE_TOOLS)
            logger.info("SQL Agent 노드 실행")
            result = await sql_agent(state)
            logger.info(f"에이전트 노드 실행 완료: {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Agent 노드 실행 오류: {e}")
            raise
    
    workflow.add_node("agent", agent_node)
    
    # 2. 도구 노드 (LangGraph 표준 ToolNode)
    tool_node = ToolNode(AVAILABLE_TOOLS)
    workflow.add_node("tools", tool_node)
    
    # ================== 라우팅 로직 ==================
    
    def should_continue_from_agent(state: SQLAgentState) -> Literal["tools", "__end__"]:
        """단순화된 Tool Condition: 도구 호출 여부만 판단"""
        messages = state.get("messages", [])
        if not messages:
            logger.info("메시지 없음 - 종료")
            return "__end__"
        
        last_message = messages[-1]
        
        # 도구 호출이 있는 경우 → tools로 이동
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"도구 호출 감지: {len(last_message.tool_calls)}개")
            return "tools"
        
        # 도구 호출이 없는 경우 → 종료 (최종 응답)
        logger.info("도구 호출 없음 - 최종 응답으로 종료")
        return "__end__"
    
    def should_continue_from_tools(state: SQLAgentState) -> Literal["agent"]:
        """도구 실행 후 항상 agent로 돌아가기"""
        logger.info("도구 실행 완료 - 에이전트로 돌아가기")
        return "agent"
    
    # ================== 엣지 설정 ==================
    
    # 단순화된 워크플로우: START → agent ↔ tools → END
    workflow.add_edge(START, "agent")
    
    # Agent에서 Tool Condition 판단
    workflow.add_conditional_edges(
        "agent",
        should_continue_from_agent,
        {
            "tools": "tools",      # 도구 호출 시
            "__end__": END         # 도구 호출 없으면 종료
        }
    )
    
    # Tools에서 Agent로 루프백
    workflow.add_conditional_edges(
        "tools",
        should_continue_from_tools,
        {
            "agent": "agent"       # 항상 에이전트로 돌아가기
        }
    )
    
    # ================== 메모리 설정 ==================
    checkpointer = None
    try:
        if settings.enable_memory and settings.DATABASE_URL:
            logger.info("PostgresSaver 연결 풀 설정 시작")
            
            # 최적화된 PostgreSQL 연결 풀 설정
            
            pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL,
                max_size=settings.POSTGRES_MAX_CONNECTIONS,  # 설정 기반 최대 연결 수
                min_size=2,  # 최소 연결 수 (항상 2개 유지)
                check=AsyncConnectionPool.check_connection,
                kwargs={
                    "autocommit": settings.POSTGRES_AUTOCOMMIT,  # 설정 기반 자동 커밋
                    "prepare_threshold": settings.POSTGRES_PREPARE_THRESHOLD,  # Prepared Statement 설정
                    "row_factory": dict_row,  # 딕셔너리 형태로 결과 반환
                }
            )
            
            # 연결 풀 열기 (대기 시간 설정)
            await pool.open(wait=True, timeout=10.0)
            logger.info(f"PostgreSQL 연결 풀 생성 완료 (max_size: {settings.POSTGRES_MAX_CONNECTIONS})")
            
            checkpointer = AsyncPostgresSaver(pool)
            
            # setup() 시 스키마 중복 생성 오류 방지
            try:
                await checkpointer.setup()
                logger.info("PostgresSaver 테이블 및 인덱스 설정 완료")
            except Exception as setup_error:
                error_msg = str(setup_error).lower()
                if ("already exists" in error_msg or 
                    ("column" in error_msg and "already exists" in error_msg) or
                    "task_path" in error_msg or
                    "transaction block" in error_msg or 
                    "concurrently" in error_msg or
                    "index" in error_msg):
                    logger.warning(f"PostgresSaver 스키마 중복 오류 무시: {setup_error}")
                    logger.info("기존 테이블/컬럼/인덱스 사용 - 정상 동작")
                    # 스키마 중복 오류는 무시하고 checkpointer 사용
                else:
                    logger.error(f"PostgresSaver setup 실패: {setup_error}")
                    # 연결 풀 정리 후 재시도
                    await pool.close()
                    raise setup_error
                    
            logger.info("PostgreSQL 기반 메모리 시스템 활성화 완료")
        else:
            logger.info("메모리 비활성화 (DATABASE_URL 없음 또는 enable_memory=False)")
    except Exception as e:
        logger.warning(f"PostgresSaver 설정 실패, InMemory로 Fallback: {e}")
        checkpointer = None
        
        # Fallback: InMemory 체크포인터 사용
        try:
            checkpointer = MemorySaver()
            logger.info("InMemory 체크포인터로 Fallback 완료")
        except Exception as fallback_error:
            logger.error(f"InMemory Fallback도 실패: {fallback_error}")
            checkpointer = None
    
    # ================== 그래프 컴파일 ==================
    logger.info("그래프 컴파일 시작...")
    try:
        graph = workflow.compile(checkpointer=checkpointer)
        logger.info("그래프 컴파일 성공!")
    except Exception as compile_error:
        logger.error(f"그래프 컴파일 실패: {compile_error}")
        raise compile_error
    
    logger.info("단순화된 SQL Agent 그래프 생성 완료")
    logger.info(f"   - 워크플로우: START → agent ↔ tools → END")
    logger.info(f"   - 메모리: {'PostgreSQL' if checkpointer else '비활성화'}")
    logger.info(f"   - 사용 가능한 도구: {len(AVAILABLE_TOOLS)}개")
    logger.info(f"   - Tool Calling: 단순 조건부 루프 방식")
    
    return graph