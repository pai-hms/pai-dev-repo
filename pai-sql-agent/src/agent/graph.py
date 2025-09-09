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
    analyze_question, execute_tools, generate_response, 
    should_continue, create_agent_state
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


async def create_sql_agent(enable_checkpointer: bool = True) -> CompiledStateGraph:
    """SQL Agent 그래프 생성 (AgentState 기반)"""
    
    # AgentState를 사용한 상태 그래프 초기화
    from src.agent.nodes import AgentState
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
        """쿼리 실행 (단일 응답) - 개선된 메모리 지원"""
        try:
            logger.info(f"🚀 쿼리 실행 시작: {question[:50]}...")
            
            # 에이전트 가져오기
            agent = await self._get_agent()
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
                logger.info(f"🔑 세션 ID 사용: {session_id}")
            
            # 기존 상태 복원 시도 (메모리 기능)
            initial_state = {}
            if self.enable_checkpointer and session_id:
                try:
                    existing_state = await agent.aget_state(config)
                    if existing_state and existing_state.values:
                        # 기존 상태에 새 질문 추가
                        initial_state = existing_state.values.copy()
                        initial_state["current_query"] = question
                        logger.info(f"💾 기존 대화 기록 로드 완료 (메시지: {len(initial_state.get('messages', []))}개)")
                    else:
                        # 새 상태 생성
                        initial_state = create_agent_state(question)
                        logger.info("🆕 새 대화 세션 시작")
                except Exception as state_error:
                    logger.warning(f"⚠️ 기존 상태 로드 실패, 새 상태 생성: {str(state_error)}")
                    initial_state = create_agent_state(question)
            else:
                # 체크포인터 사용하지 않는 경우
                initial_state = create_agent_state(question)
                logger.info("🔧 메모리 없이 실행")
            
            # 현재 질문을 상태에 업데이트
            initial_state["current_query"] = question
            
            # 그래프 실행
            logger.info("⚙️ 그래프 실행 시작")
            result = await agent.ainvoke(initial_state, config=config)
            
            logger.info("✅ 쿼리 실행 완료")
            return result
            
        except Exception as e:
            # 더 자세한 예외 정보 로깅
            error_details = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"❌ 쿼리 실행 중 오류: {error_details}")
            
            return {
                "error_message": f"쿼리 실행 중 오류가 발생했습니다: {str(e) or type(e).__name__}",
                "is_complete": True,
                "messages": [],
                "current_query": question,
                "sql_results": [],
                "used_tools": [],
                "iteration_count": 0,
                "max_iterations": 10
            }
    
    async def stream_query(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """쿼리 실행 (스트리밍) - 개선된 메모리 지원"""
        try:
            logger.info(f"🚀 스트리밍 쿼리 시작: {question[:50]}...")
            
            # 에이전트 가져오기
            agent = await self._get_agent()
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
                logger.info(f"🔑 세션 ID 사용: {session_id}")
            
            # 기존 상태 복원 시도 (메모리 기능)
            initial_state = {}
            if self.enable_checkpointer and session_id:
                try:
                    existing_state = await agent.aget_state(config)
                    if existing_state and existing_state.values:
                        # 기존 상태에 새 질문 추가
                        initial_state = existing_state.values.copy()
                        initial_state["current_query"] = question
                        logger.info(f"💾 기존 대화 기록 로드 완료 (메시지: {len(initial_state.get('messages', []))}개)")
                    else:
                        # 새 상태 생성
                        initial_state = create_agent_state(question)
                        logger.info("🆕 새 대화 세션 시작")
                except Exception as state_error:
                    logger.warning(f"⚠️ 기존 상태 로드 실패, 새 상태 생성: {str(state_error)}")
                    initial_state = create_agent_state(question)
            else:
                # 체크포인터 사용하지 않는 경우
                initial_state = create_agent_state(question)
                logger.info("🔧 메모리 없이 실행")
            
            # 현재 질문을 상태에 업데이트
            initial_state["current_query"] = question
            
            # 그래프 스트리밍 실행 - messages 모드로 LLM 토큰 스트리밍
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
            # 에이전트 가져오기
            agent = await self._get_agent()
            
            # 설정 생성
            config = None
            if self.enable_checkpointer and session_id:
                config = {"configurable": {"thread_id": session_id}}
            
            # 기존 상태 복원 시도 (메모리 기능)
            initial_state = {}
            if self.enable_checkpointer and session_id:
                try:
                    existing_state = await agent.aget_state(config)
                    if existing_state and existing_state.values:
                        initial_state = existing_state.values.copy()
                        initial_state["current_query"] = question
                    else:
                        initial_state = create_agent_state(question)
                except Exception:
                    initial_state = create_agent_state(question)
            else:
                initial_state = create_agent_state(question)
            
            initial_state["current_query"] = question
            
            # 그래프 스트리밍 실행 - 다중 모드
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