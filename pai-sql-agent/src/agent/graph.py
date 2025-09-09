"""
LangGraph 그래프 정의
에이전트의 워크플로우를 정의하고 관리
"""
import logging
import traceback
from typing import Dict, Any, AsyncGenerator, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

# PostgreSQL 체크포인터 import
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from src.agent.nodes import (
    analyze_question, execute_tools, generate_response, 
    should_continue, create_agent_state
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


async def create_checkpointer():
    """체크포인터 생성"""
    if not POSTGRES_AVAILABLE:
        logger.warning("PostgreSQL 체크포인터를 사용할 수 없습니다. MemorySaver를 사용합니다.")
        return MemorySaver()
    
    try:
        settings = get_settings()
        
        # DATABASE_URL 파싱
        db_url = settings.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url[13:]
        
        # 비동기 연결 풀 생성
        pool = AsyncConnectionPool(
            conninfo=f"postgresql://{db_url}",
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
            }
        )
        
        # AsyncPostgresSaver 생성
        checkpointer = AsyncPostgresSaver(pool)
        
        # 테이블 자동 생성
        await checkpointer.setup()
        
        logger.info("PostgreSQL 체크포인터가 성공적으로 설정되었습니다.")
        return checkpointer
        
    except Exception as e:
        logger.error(f"PostgreSQL 체크포인터 생성 실패: {e}")
        logger.info("MemorySaver로 대체합니다.")
        return MemorySaver()


async def create_sql_agent(enable_checkpointer: bool = True) -> CompiledStateGraph:
    """SQL Agent 그래프 생성"""
    
    # 상태 그래프 초기화
    workflow = StateGraph(dict)
    
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


class SQLAgentService:
    """SQL Agent 서비스"""
    
    def __init__(self, enable_checkpointer: bool = True):
        self.enable_checkpointer = enable_checkpointer
        self._agent = None
    
    async def _get_agent(self):
        """지연 초기화로 에이전트 생성"""
        if self._agent is None:
            self._agent = await create_sql_agent(self.enable_checkpointer)
        return self._agent
    
    async def invoke_query(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """쿼리 실행 (단일 응답)"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
            
            # 그래프 실행
            agent = await self._get_agent()
            result = await agent.ainvoke(initial_state, config=config)
            
            return result
            
        except Exception as e:
            # 더 자세한 예외 정보 로깅
            error_details = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"쿼리 실행 중 오류: {error_details}")
            
            return {
                "error_message": f"쿼리 실행 중 오류가 발생했습니다: {str(e) or type(e).__name__}",
                "is_complete": True,
                "messages": []
            }
    
    async def stream_query(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """쿼리 실행 (스트리밍)"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
            
            # 그래프 스트리밍 실행
            agent = await self._get_agent()
            async for chunk in agent.astream(initial_state, config=config):
                yield chunk
                
        except Exception as e:
            logger.error(f"스트리밍 쿼리 실행 중 오류: {str(e)}")
            yield {
                "error_message": f"스트리밍 실행 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True,
                "messages": []
            }
    
    async def get_chat_history(self, session_id: str) -> list:
        """채팅 기록 조회"""
        if not self.enable_checkpointer:
            return []
        
        try:
            config = {"configurable": {"thread_id": session_id}}
            agent = await self._get_agent()
            state = await agent.aget_state(config)
            return state.values.get("messages", [])
        except Exception as e:
            logger.error(f"채팅 기록 조회 중 오류: {str(e)}")
            return []


# 전역 서비스 인스턴스
_sql_agent_service: Optional[SQLAgentService] = None


def get_sql_agent_service(enable_checkpointer: bool = True) -> SQLAgentService:
    """SQL Agent 서비스 인스턴스 반환"""
    global _sql_agent_service
    if _sql_agent_service is None:
        _sql_agent_service = SQLAgentService(enable_checkpointer=enable_checkpointer)
    return _sql_agent_service


# 하위 호환성을 위한 기존 함수들
def get_sql_agent_graph(enable_checkpointer: bool = True):
    """하위 호환성을 위한 래퍼 함수"""
    return get_sql_agent_service(enable_checkpointer)


async def create_session_config(session_id: str) -> Dict[str, Any]:
    """세션 설정 생성"""
    return {
        "configurable": {
            "thread_id": session_id
        }
    }