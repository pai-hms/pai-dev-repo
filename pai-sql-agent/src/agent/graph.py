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
    """
    PostgreSQL 체크포인터 생성 (비동기 방식)
    
    참고 문서에 따른 최적화된 구현:
    - AsyncPostgresSaver 사용
    - 컨텍스트 매니저 적용
    - 자동 테이블 생성
    """
    if not POSTGRES_AVAILABLE:
        logger.warning("PostgreSQL 체크포인터를 사용할 수 없습니다. MemorySaver를 사용합니다.")
        return MemorySaver()
    
    try:
        settings = get_settings()
        
        # DATABASE_URL을 PostgreSQL 체크포인터용으로 변환
        # 예: postgresql://user:pass@host:port/db 형태로 변환
        db_url = settings.database_url
        
        # 연결 풀 생성 (영속적 연결 풀)
        pool = AsyncConnectionPool(
            conninfo=db_url,
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
            }
        )
        
        # 풀 열기
        await pool.open()
        
        # AsyncPostgresSaver 생성
        checkpointer = AsyncPostgresSaver(pool)
        
        # 테이블 자동 생성 (setup 호출)
        await checkpointer.setup()
        
        logger.info("PostgreSQL 체크포인터가 성공적으로 설정되었습니다.")
        logger.info(f"Database URL: {db_url[:50]}...")
        
        return checkpointer
        
    except Exception as e:
        logger.error(f"PostgreSQL 체크포인터 생성 실패: {e}")
        logger.error(f"Database URL: {settings.database_url[:50]}...")
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
    """SQL Agent 서비스 (영속성 관리 포함)"""
    
    def __init__(self, enable_checkpointer: bool = True):
        self.enable_checkpointer = enable_checkpointer
        self._agent = None
        self._checkpointer = None
    
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
        """쿼리 실행 (스트리밍) - LLM 토큰별 스트리밍"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
            
            # 그래프 스트리밍 실행 - messages 모드로 LLM 토큰 스트리밍
            agent = await self._get_agent()
            final_state = None
            
            async for message_chunk, metadata in agent.astream(
                initial_state, 
                config=config,
                stream_mode="messages"  # LLM 토큰별 스트리밍
            ):
                # LLM 토큰이 있으면 바로 전달
                if hasattr(message_chunk, 'content') and message_chunk.content:
                    yield {
                        "type": "token",
                        "content": message_chunk.content,
                        "metadata": metadata
                    }
            
            # 스트리밍 완료 후 최종 상태 조회 (도구 정보 포함)
            try:
                final_state = await agent.aget_state(config)
                if final_state and hasattr(final_state, 'values'):
                    state_values = final_state.values
                    
                    # 최종 상태 정보 전달 (도구 정보 포함)
                    yield {
                        "type": "final_state",
                        "content": {
                            "used_tools": state_values.get("used_tools", []),
                            "sql_results": state_values.get("sql_results", []),
                            "is_complete": state_values.get("is_complete", True)
                        }
                    }
            except Exception as state_error:
                logger.warning(f"최종 상태 조회 실패: {str(state_error)}")
                
        except Exception as e:
            logger.error(f"스트리밍 쿼리 실행 중 오류: {str(e)}")
            yield {
                "type": "error",
                "content": f"스트리밍 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def stream_query_with_updates(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """쿼리 실행 (혼합 스트리밍) - 토큰 + 업데이트"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
            
            # 그래프 스트리밍 실행 - 다중 모드
            agent = await self._get_agent()
            async for stream_mode, chunk in agent.astream(
                initial_state, 
                config=config,
                stream_mode=["messages", "updates"]  # 토큰 + 노드 업데이트
            ):
                if stream_mode == "messages":
                    # LLM 토큰 스트리밍
                    message_chunk, metadata = chunk
                    if hasattr(message_chunk, 'content') and message_chunk.content:
                        yield {
                            "type": "token",
                            "content": message_chunk.content,
                            "metadata": metadata
                        }
                elif stream_mode == "updates":
                    # 노드 업데이트
                    yield {
                        "type": "update",
                        "content": chunk
                    }
                
        except Exception as e:
            logger.error(f"스트리밍 쿼리 실행 중 오류: {str(e)}")
            yield {
                "type": "error",
                "content": f"스트리밍 실행 중 오류가 발생했습니다: {str(e)}"
            }

    async def _get_checkpointer(self):
        """체크포인터 인스턴스 반환"""
        if self._checkpointer is None and self.enable_checkpointer:
            self._checkpointer = await create_checkpointer()
        return self._checkpointer

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

    async def get_state_history(self, session_id: str, limit: int = 10) -> list:
        """상태 히스토리 조회 (최신 LangGraph 방식)"""
        if not self.enable_checkpointer:
            return []
        
        try:
            config = {"configurable": {"thread_id": session_id}}
            agent = await self._get_agent()
            
            # 최신 방식으로 상태 히스토리 조회
            history = []
            async for state in agent.aget_state_history(config, limit=limit):
                history.append({
                    "config": state.config,
                    "values": state.values,
                    "metadata": state.metadata,
                    "created_at": state.created_at.isoformat() if state.created_at else None,
                    "step": state.metadata.get("step", 0)
                })
            
            return history
        except Exception as e:
            logger.error(f"상태 히스토리 조회 중 오류: {str(e)}")
            return []

    async def delete_thread(self, session_id: str) -> bool:
        """세션(스레드) 삭제"""
        if not self.enable_checkpointer:
            return False
        
        try:
            checkpointer = await self._get_checkpointer()
            if checkpointer and hasattr(checkpointer, 'adelete_thread'):
                await checkpointer.adelete_thread(session_id)
                logger.info(f"세션 삭제 완료: {session_id}")
                return True
            else:
                logger.warning("체크포인터에서 스레드 삭제를 지원하지 않습니다.")
                return False
        except Exception as e:
            logger.error(f"세션 삭제 중 오류: {str(e)}")
            return False

    async def list_checkpoints(self, session_id: str, limit: int = 10) -> list:
        """체크포인트 목록 조회"""
        if not self.enable_checkpointer:
            return []
        
        try:
            checkpointer = await self._get_checkpointer()
            if checkpointer and hasattr(checkpointer, 'alist'):
                config = {"configurable": {"thread_id": session_id}}
                
                checkpoints = []
                async for checkpoint_tuple in checkpointer.alist(config, limit=limit):
                    checkpoints.append({
                        "config": checkpoint_tuple.config,
                        "checkpoint": checkpoint_tuple.checkpoint,
                        "metadata": checkpoint_tuple.metadata,
                        "parent_config": checkpoint_tuple.parent_config
                    })
                
                return checkpoints
            else:
                logger.warning("체크포인터에서 체크포인트 목록 조회를 지원하지 않습니다.")
                return []
        except Exception as e:
            logger.error(f"체크포인트 목록 조회 중 오류: {str(e)}")
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