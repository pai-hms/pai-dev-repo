"""
실시간 토큰 스트리밍 전용 서비스
LangGraph의 astream을 활용한 실제 토큰 스트리밍 구현
"""
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleTokenStreamingService:
    """
    실시간 토큰 스트리밍 전용 서비스
    LangGraph의 astream을 활용한 실제 토큰 스트리밍 구현
    """
    
    def __init__(self, agent_graph, session_service):
        """
        의존성 주입을 통한 초기화
        
        Args:
            agent_graph: LangGraph 에이전트 그래프
            session_service: 세션 관리 서비스 (None일 수 있음)
        """
        self._agent_graph = agent_graph
        self._session_service = session_service
        
        if self._session_service is None:
            logger.warning("⚠️ 세션 서비스가 None입니다. 세션 관리 기능이 비활성화됩니다.")
    
    async def stream_llm_tokens(
        self,
        user_input: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🌊 실제 LLM 토큰 단위 스트리밍
        """
        start_time = datetime.now()
        thread_id = thread_id or session_id or f"stream_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"🌊 실시간 토큰 스트리밍 시작 (thread_id: {thread_id})")
            
            # 세션 관리 (안전하게 처리)
            await self._manage_session_safely(thread_id, user_input)
            
            # LangGraph 설정
            config = {"configurable": {"thread_id": thread_id}}
            
            # 초기 상태 생성
            from .nodes import create_react_initial_state
            input_data = create_react_initial_state(user_input, thread_id)
            
            # LangGraph astream_events로 실제 토큰 스트리밍
            # astream_events를 사용하면 LLM의 실제 토큰 이벤트를 받을 수 있음
            async for event in self._agent_graph.astream_events(
                input_data,
                config=config,
                version="v1"  # 이벤트 버전
            ):
                # 실제 LLM 토큰 이벤트 처리
                async for token_chunk in self._process_llm_event(
                    event, start_time, thread_id
                ):
                    yield token_chunk
            
            # 완료 신호
            yield {
                "type": "complete",
                "content": "✅ 응답 생성 완료",
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            }
                    
        except Exception as e:
            logger.error(f"❌ 토큰 스트리밍 실패: {e}")
            yield {
                "type": "error",
                "content": f"❌ 스트리밍 오류: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            }
    
    async def _process_llm_event(
        self,
        event: Dict[str, Any],
        start_time: datetime,
        thread_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        실제 LLM 이벤트를 처리하여 토큰 스트리밍
        """
        current_time = datetime.now()
        elapsed_time = (current_time - start_time).total_seconds()
        
        base_data = {
            "timestamp": current_time.isoformat(),
            "elapsed_time": elapsed_time,
            "thread_id": thread_id
        }
        
        try:
            event_type = event.get("event", "")
            event_data = event.get("data", {})
            
            # LLM 스트리밍 토큰 이벤트
            if event_type == "on_chat_model_stream":
                # 실제 LLM 토큰 청크
                chunk = event_data.get("chunk", {})
                if hasattr(chunk, 'content') and chunk.content:
                    yield {
                        **base_data,
                        "type": "token",
                        "content": chunk.content,
                        "node": event.get("name", "llm"),
                        "run_id": event.get("run_id")
                    }
            
            # 도구 실행 이벤트
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                yield {
                    **base_data,
                    "type": "tool_start",
                    "content": f"🛠️ {tool_name} 실행 시작",
                    "tool_name": tool_name,
                    "run_id": event.get("run_id")
                }
            
            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown_tool")
                output = event_data.get("output", "")
                yield {
                    **base_data,
                    "type": "tool_execution",
                    "content": {
                        "tool_name": tool_name,
                        "output": str(output)[:200] + "..." if len(str(output)) > 200 else str(output)
                    },
                    "tool_name": tool_name,
                    "run_id": event.get("run_id")
                }
            
            # 체인 시작/종료 이벤트
            elif event_type == "on_chain_start":
                chain_name = event.get("name", "unknown_chain")
                if chain_name != "__start__":  # 시작 체인은 무시
                    yield {
                        **base_data,
                        "type": "node_update",
                        "content": f"🔄 {chain_name} 시작",
                        "node": chain_name,
                        "run_id": event.get("run_id")
                    }
            
            elif event_type == "on_chain_end":
                chain_name = event.get("name", "unknown_chain")
                if chain_name != "__end__":  # 종료 체인은 무시
                    yield {
                        **base_data,
                        "type": "node_update",
                        "content": f"✅ {chain_name} 완료",
                        "node": chain_name,
                        "run_id": event.get("run_id")
                    }
                    
        except Exception as e:
            logger.error(f"❌ LLM 이벤트 처리 실패: {e}")
            yield {
                **base_data,
                "type": "error",
                "content": f"이벤트 처리 오류: {str(e)}",
                "error": str(e)
            }
    
    async def _manage_session_safely(self, thread_id: str, user_input: str):
        """세션 관리 (안전한 버전 - 세션 서비스가 None이어도 처리)"""
        try:
            if self._session_service is None:
                logger.debug(f"세션 서비스가 없어 세션 관리를 건너뜁니다 (thread_id: {thread_id})")
                return
                
            # 기존 세션 확인
            session = await self._session_service.get_session_by_thread_id(thread_id)
            
            if not session:
                # 새 세션 생성
                session = await self._session_service.start_new_session(
                    title=user_input[:50] + "..." if len(user_input) > 50 else user_input,
                    custom_thread_id=thread_id
                )
                logger.info(f"새 세션 생성: {session.session_id}")
            else:
                # 기존 세션 활동 업데이트
                await self._session_service.update_session_activity(
                    session.session_id, 
                    increment_message=True
                )
                logger.info(f"세션 활동 업데이트: {session.session_id}")
                
        except Exception as e:
            logger.warning(f"세션 관리 실패 (계속 진행): {e}")


class StreamingService:
    """
    DEPRECATED: SimpleTokenStreamingService 사용
    하위 호환성을 위해 유지
    """
    
    def __init__(self, agent_graph, session_service):
        logger.warning("StreamingService는 deprecated입니다. SimpleTokenStreamingService를 사용하세요.")
        self._simple_service = SimpleTokenStreamingService(agent_graph, session_service)
    
    async def stream_llm_tokens(self, *args, **kwargs):
        """하위 호환성을 위한 래퍼"""
        async for chunk in self._simple_service.stream_llm_tokens(*args, **kwargs):
            yield chunk


# 팩토리 함수들
async def create_streaming_service(agent_graph, session_service=None):
    """스트리밍 서비스 생성"""
    return SimpleTokenStreamingService(agent_graph, session_service)


def get_streaming_service_class():
    """스트리밍 서비스 클래스 반환"""
    return SimpleTokenStreamingService


# 하위 호환성을 위한 별칭
TokenStreamingService = SimpleTokenStreamingService