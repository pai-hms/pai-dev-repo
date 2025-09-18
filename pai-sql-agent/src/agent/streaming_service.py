"""
실시간 스트리밍 서비스 - 간소화된 버전
"""
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamingService:
    """실시간 스트리밍 서비스"""
    
    def __init__(self, agent_graph, session_service=None):
        self._agent_graph = agent_graph
        self._session_service = session_service
    
    async def stream_tokens(
        self,
        user_input: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """토큰 스트리밍"""
        try:
            thread_id = thread_id or session_id or f"stream_{int(datetime.now().timestamp())}"
            
            # 초기 상태 생성
            from .nodes import create_initial_state
            initial_state = create_initial_state(user_input, thread_id)
            
            # 스트리밍 설정
            config = {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 50
            }
            
            # 시작 신호
            yield {
                "type": "start",
                "content": "처리 시작",
                "timestamp": datetime.now().isoformat()
            }
            
            # 스트리밍 실행
            async for event in self._agent_graph.astream_events(
                initial_state,
                config=config,
                version="v1"
            ):
                event_type = event.get("event", "")
                
                if event_type == "on_chain_stream":
                    chunk = event.get("data", {}).get("chunk", {})
                    if hasattr(chunk, 'content') and chunk.content:
                        yield {
                            "type": "token",
                            "content": chunk.content,
                            "timestamp": datetime.now().isoformat()
                        }
                
                elif event_type == "on_tool_start":
                    yield {
                        "type": "tool_start",
                        "tool": event.get("name", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                
                elif event_type == "on_tool_end":
                    yield {
                        "type": "tool_end",
                        "tool": event.get("name", ""),
                        "result": str(event.get("data", {}).get("output", ""))[:200],
                        "timestamp": datetime.now().isoformat()
                    }
            
            # 완료 신호
            yield {
                "type": "done",
                "content": "처리 완료",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            yield {
                "type": "error",
                "content": f"오류: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# 하위 호환성
SimpleTokenStreamingService = StreamingService