"""
SQL Agent 서비스 - Supervisor 패턴
외부 세계와의 유일한 접점 (Façade)
"""
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from .graph import create_sql_agent_graph
from .nodes import create_initial_state
from .container import get_container

logger = logging.getLogger(__name__)


class SQLAgentService:
    """SQL Agent 서비스 (Supervisor 패턴)"""
    
    _instance: Optional['SQLAgentService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._agent_graph = None
        self._session_service = None
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'SQLAgentService':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """서비스 초기화"""
        if self._initialized:
            return
            
        logger.info("SQL Agent 서비스 초기화 시작")
        
        try:
            # DI 컨테이너 초기화
            container = await get_container()
            
            # SQL Agent 그래프 생성
            self._agent_graph = await create_sql_agent_graph()
            
            # 세션 서비스 초기화 (컨테이너에서 가져오기)
            from .container import get_session_service
            self._session_service = await get_session_service()  
            
            self._initialized = True
            logger.info("SQL Agent 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"SQL Agent 서비스 초기화 실패: {e}")
            self._initialized = False
            raise
    
    async def process_query(
        self,
        question: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """질문 처리 (비스트리밍)"""
        try:
            if not self._initialized:
                await self._initialize()
            
            # 초기 상태 생성
            initial_state = create_initial_state(question, thread_id or session_id or "default")
            
            # 그래프 실행
            config = {
                "configurable": {"thread_id": thread_id or session_id or "default"},
                "recursion_limit": 50
            }
            
            result = await self._agent_graph.ainvoke(initial_state, config=config)
            
            logger.info(f"쿼리 처리 완료: {question[:50]}...")
            
            return {
                "success": True,
                "result": result.get("data", ""),
                "sql_query": result.get("sql_query", ""),
                "messages": result.get("messages", [])
            }
            
        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": f"처리 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def process_query_stream(
        self,
        question: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """질문 처리 (기존 스트리밍 + UI 진행상황 추가)"""
        try:
            if not self._initialized:
                await self._initialize()
        
            # 초기 상태 생성
            initial_state = create_initial_state(question, thread_id or session_id or "default")
        
            config = {
                "configurable": {"thread_id": thread_id or session_id or "default"},
                "recursion_limit": 50
            }
        
            # 시작 신호
            yield {
                "type": "start",
                "content": "SQL 분석을 시작합니다...",
                "timestamp": datetime.now().isoformat()
            }
            
            # 디버깅 카운터
            chunk_count = 0
            token_count = 0
            
            
            # **🎯 UI 진행상황 모니터링 (추가 기능)**
            async def ui_progress_monitor():
                """UI용 진행상황 이벤트만 별도로 스트리밍 (중복 제거)"""
                seen_events = set()  # ✅ 중복 이벤트 추적
                
                try:
                    async for event in self._agent_graph.astream_events(
                        initial_state, config=config, version="v1"
                    ):
                        event_type = event.get("event", "")
                        event_name = event.get("name", "")
                        
                        # ✅ 이벤트 고유 키 생성
                        event_key = f"{event_type}:{event_name}"
                        
                        # 노드 시작 이벤트 (중복 방지)
                        if event_type == "on_chain_start":
                            if event_key not in seen_events:
                                seen_events.add(event_key)
                                
                                if "agent" in event_name.lower():
                                    yield {
                                        "type": "progress",
                                        "content": "🤖 SQLAgentNode 실행 시작",
                                        "timestamp": datetime.now().isoformat()
                                    }
                                elif "tools" in event_name.lower():
                                    yield {
                                        "type": "progress", 
                                        "content": "🔧 도구 실행 단계 진입",
                                        "timestamp": datetime.now().isoformat()
                                    }
                                elif "response" in event_name.lower():
                                    yield {
                                        "type": "progress",
                                        "content": "💬 사용자 친화적 응답 생성 중...",
                                        "timestamp": datetime.now().isoformat()
                                    }
                        
                        # LLM 추론 시작
                        elif event_type == "on_chat_model_start":
                            yield {
                                "type": "progress",
                                "content": "🧠 LLM 추론 시작 - 질문 분석 및 도구 선택...",
                                "timestamp": datetime.now().isoformat()
                            }
                        
                        # 도구 이벤트 (도구별로 한 번만)
                        elif event_type == "on_tool_start":
                            tool_name = event.get("name", "Unknown")
                            tool_key = f"tool_start:{tool_name}"
                            
                            if tool_key not in seen_events:
                                seen_events.add(tool_key)
                                yield {
                                    "type": "progress",
                                    "content": f"🔧 {tool_name} 도구 호출됨",
                                    "timestamp": datetime.now().isoformat()
                                }
                        
                        # 도구 실행 완료
                        elif event_type == "on_tool_end":
                            tool_name = event.get("name", "Unknown")
                            tool_key = f"tool_end:{tool_name}"
                            
                            if tool_key not in seen_events:
                                seen_events.add(tool_key)
                                output = event.get("data", {}).get("output", "")
                                result_count = "결과 있음" if output and "데이터 없음" not in str(output) else "결과 없음"
                                
                                yield {
                                    "type": "progress",
                                    "content": f"📊 {tool_name} 실행 완료 - {result_count}",
                                    "timestamp": datetime.now().isoformat()
                                }
                
                except Exception as e:
                    logger.error(f"UI 진행상황 모니터링 오류: {e}")
            
            # **병렬 실행: 기존 스트리밍 + UI 진행상황**
            async def merge_streams():
                """기존 토큰 스트리밍과 UI 진행상황을 병합"""
                
                # UI 진행상황 스트림
                ui_stream = ui_progress_monitor()
                
                # 기존 토큰 스트리밍
                token_stream = self._agent_graph.astream(
                    initial_state,
                    config=config,
                    stream_mode="messages"
                )
                
                # 두 스트림을 병합
                ui_task = None
                
                try:
                    # UI 모니터링 태스크 시작
                    ui_gen = aiter(ui_stream)
                    ui_task = asyncio.create_task(anext(ui_gen))
                    
                    # 메인 토큰 스트리밍
                    async for chunk in token_stream:
                        nonlocal chunk_count, token_count
                        chunk_count += 1
                        
                        # UI 이벤트 체크 (논블로킹)
                        if ui_task and ui_task.done():
                            try:
                                ui_event = ui_task.result()
                                yield ui_event
                                # 다음 UI 이벤트 대기
                                ui_task = asyncio.create_task(anext(ui_gen))
                            except StopAsyncIteration:
                                ui_task = None
                            except Exception as e:
                                logger.warning(f"UI 이벤트 처리 오류: {e}")
                                ui_task = None
                        
                        # 기존 토큰 스트리밍 로직 (변경 없음)
                        if isinstance(chunk, tuple) and len(chunk) >= 1:
                            message = chunk[0] if len(chunk) > 0 else None
                            metadata = chunk[1] if len(chunk) > 1 else None
                            
                            if message and hasattr(message, 'content'):
                                logger.info(f"   Content: '{message.content[:50]}...'")
                            
                            # response 노드에서만 토큰 스트리밍
                            if (message and 
                                hasattr(message, 'content') and 
                                message.content and  
                                message.content.strip() and
                                metadata and
                                metadata.get('langgraph_node') == 'response'):
                                
                                token_count += 1
                                yield {
                                    "type": "token",
                                    "content": message.content,
                                    "timestamp": datetime.now().isoformat()
                                }
                            
                            # 노드 업데이트
                            elif metadata and metadata.get('langgraph_node'):
                                node_name = metadata.get('langgraph_node')
                                yield {
                                    "type": "node_update",
                                    "node": node_name,
                                    "content": f"🔄 {node_name} 실행 중...",
                                    "timestamp": datetime.now().isoformat()
                                }
                        
                        else:
                            logger.warning(f"⚠️ 예상치 못한 chunk 형태: {type(chunk)}")
                    
                    # 남은 UI 이벤트들 처리
                    while ui_task and not ui_task.done():
                        try:
                            ui_event = await ui_task
                            yield ui_event
                            ui_task = asyncio.create_task(anext(ui_gen))
                        except StopAsyncIteration:
                            break
                        except Exception as e:
                            logger.warning(f"남은 UI 이벤트 처리 오류: {e}")
                            break
                    
                finally:
                    # 정리
                    if ui_task and not ui_task.done():
                        ui_task.cancel()
                
                logger.info(f"📊 스트리밍 완료 - 총 chunk: {chunk_count}, 토큰: {token_count}")
            
            # **LangGraph 공식 방식 + UI 진행상황**
            try:
                logger.info("🔍 스트리밍 시작 - stream_mode='messages' + UI 진행상황")
                
                async for result_chunk in merge_streams():
                    yield result_chunk
            
            except Exception as stream_error:
                logger.error(f"❌ 스트리밍 오류: {stream_error}")
                
                # Fallback 처리...
                try:
                    result = await self._agent_graph.ainvoke(initial_state, config=config)
                    
                    if "messages" in result:
                        for message in reversed(result["messages"]):
                            if (hasattr(message, 'type') and 
                                message.type == "ai" and 
                                message.content):
                                
                                for char in message.content:
                                    yield {
                                        "type": "token",
                                        "content": char,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                break
                        
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback 오류: {fallback_error}")
                    yield {
                        "type": "error",
                        "content": "응답을 생성할 수 없습니다.",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # 완료 신호
            yield {
                "type": "done",
                "content": "✅ SQL 분석이 완료되었습니다.",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 전체 스트리밍 처리 실패: {e}")
            yield {
                "type": "error",
                "content": f"❌ 처리 중 오류가 발생했습니다: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

async def _monitor_events(self, initial_state, config):
    """이벤트 모니터링 (도구 실행, 노드 상태)"""
    async for event in self._agent_graph.astream_events(
        initial_state, config=config, version="v1"
    ):
        event_type = event.get("event", "")
        event_name = event.get("name", "")
        
        if event_type == "on_tool_start":
            yield {
                "type": "tool_start",
                "tool": event.get("name", ""),
                "content": f"🔧 {event.get('name', '')} 실행 중...",
                "timestamp": datetime.now().isoformat()
            }
        
        elif event_type == "on_tool_end":
            yield {
                "type": "tool_end",
                "tool": event.get("name", ""),
                "content": f"✅ {event.get('name', '')} 완료",
                "timestamp": datetime.now().isoformat()
            }


# 편의성을 위한 전역 함수들
async def get_sql_agent_service() -> SQLAgentService:
    """SQL Agent 서비스 인스턴스 반환"""
    return await SQLAgentService.get_instance()


# 하위 호환성을 위한 별칭
get_unified_agent_service = get_sql_agent_service
get_main_agent_service = get_sql_agent_service
