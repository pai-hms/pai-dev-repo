"""
LangGraph 그래프 정의
에이전트의 워크플로우를 정의하고 관리
"""
import logging
import traceback
from typing import Dict, Any, AsyncGenerator, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage

# PostgreSQL 체크포인터 import (LangGraph 공식 방식)
try:
    from langgraph.checkpoint.postgres import AsyncPostgresSaver
    POSTGRES_AVAILABLE = True
except ImportError:
    try:
        # 대안 경로 시도
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        POSTGRES_AVAILABLE = True
    except ImportError:
        POSTGRES_AVAILABLE = False

from src.agent.nodes import (
    AgentState, create_agent_state,
    analyze_question, execute_tools, generate_response, should_continue
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# 체크포인터 상태 로깅
if POSTGRES_AVAILABLE:
    logger.info("✅ LangGraph AsyncPostgresSaver 사용 가능")
else:
    logger.warning("❌ LangGraph AsyncPostgresSaver 사용 불가, MemorySaver로 대체")


async def create_checkpointer():
    """
    LangGraph 공식 AsyncPostgresSaver 생성
    
    공식 문서 방식:
    - AsyncPostgresSaver.from_conn_string() 사용
    - 컨텍스트 매니저로 리소스 관리
    - setup() 호출로 테이블 자동 생성
    """
    if not POSTGRES_AVAILABLE:
        logger.warning("PostgreSQL 체크포인터를 사용할 수 없습니다. MemorySaver를 사용합니다.")
        return MemorySaver()
    
    try:
        settings = get_settings()
        
        # DATABASE_URL을 PostgreSQL 체크포인터용으로 변환
        db_url = settings.database_url
        
        # SQLAlchemy 형식에서 psycopg 형식으로 변환 (필요시)
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        elif db_url.startswith("postgresql+psycopg://"):
            db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        
        # sslmode가 없으면 추가
        if "sslmode=" not in db_url:
            separator = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{separator}sslmode=disable"
        
        logger.info(f"🔗 체크포인터 연결 문자열: {db_url[:50]}...")
        
        # LangGraph 공식 방식: AsyncPostgresSaver.from_conn_string 사용
        # 실제로는 컨텍스트 매니저를 사용해야 하지만, 전역 체크포인터를 위해 직접 생성
        checkpointer = None
        
        async def setup_checkpointer():
            nonlocal checkpointer
            # from_conn_string은 컨텍스트 매니저이므로 직접 사용할 수 없음
            # 대신 동일한 로직을 직접 구현
            try:
                # AsyncPostgresSaver를 직접 생성하는 대신 공식 방식 사용을 시도
                import psycopg_pool
                
                # 연결 풀 생성
                pool = psycopg_pool.AsyncConnectionPool(
                    conninfo=db_url,
                    max_size=10,
                    kwargs={
                        "autocommit": True,
                        "prepare_threshold": 0,
                    }
                )
                
                # 풀 열기
                await pool.open()
                
                # AsyncPostgresSaver 생성
                checkpointer = AsyncPostgresSaver(pool)
                
                # 테이블 설정
                await checkpointer.setup()
                
                logger.info("✅ AsyncPostgresSaver 체크포인터 설정 완료")
                return checkpointer
                
            except Exception as e:
                logger.error(f"❌ 공식 방식 설정 실패: {e}")
                raise
        
        return await setup_checkpointer()
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL 체크포인터 생성 실패: {e}")
        logger.error(f"Database URL: {settings.database_url[:50]}...")
        logger.warning("🔄 MemorySaver로 대체합니다.")
        return MemorySaver()


async def create_sql_agent_graph(enable_checkpointer: bool = True):
    """SQL Agent 그래프 생성"""
    
    # 그래프 생성
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("analyze_question", analyze_question)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("generate_response", generate_response)
    
    # 엣지 추가
    workflow.add_edge(START, "analyze_question")
    
    # 조건부 엣지 추가
    workflow.add_conditional_edges(
        "analyze_question",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "generate_response": "generate_response",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "execute_tools",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "generate_response": "generate_response",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_response",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "generate_response": "generate_response",
            "end": END
        }
    )
    
    # 컴파일
    if enable_checkpointer:
        checkpointer = await create_checkpointer()
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# 하위 호환성을 위한 함수 (service.py로 이동됨)
async def create_sql_agent(enable_checkpointer: bool = True):
    """하위 호환성을 위한 래퍼 함수"""
    return await create_sql_agent_graph(enable_checkpointer)