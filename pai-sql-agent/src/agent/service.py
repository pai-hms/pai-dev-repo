"""
SQL Agent 서비스 - Supervisor 패턴
"""
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from .graph import create_sql_agent_graph
from .nodes import create_initial_state

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
            # SQL Agent 그래프 생성
            self._agent_graph = await create_sql_agent_graph()
            
            # ✅ PostgresSaver 사용으로 별도 세션 서비스 불필요
            # self._session_service = await get_session_service()   
            
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
            initial_state = await create_initial_state(question, thread_id or session_id or "default")
            
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
        
            # ✅ 세션 히스토리를 포함한 초기 상태 생성
            initial_state = await create_initial_state(question, thread_id or session_id or "default")
        
            config = {
                "configurable": {"thread_id": thread_id or session_id or "default"},
                "recursion_limit": 50
            }
            
            # 최종 응답 저장을 위한 변수
            final_response = None
        
            # 시작 신호
            yield {
                "type": "start",
                "content": "SQL 분석을 시작합니다...",
                "timestamp": datetime.now().isoformat()
            }
            
            # 디버깅 카운터
            chunk_count = 0
            token_count = 0
            
            
            # **🎯 단일 스트림으로 통합 (중복 실행 방지)**
            
            # **단순화된 스트리밍 (중복 실행 방지)**
            async def merge_streams():
                """단일 스트림으로 토큰 및 진행상황 모니터링"""
                
                # ✅ 하나의 스트림만 사용
                token_stream = self._agent_graph.astream(
                    initial_state,
                    config=config,
                    stream_mode="messages"
                )
                
                try:
                    # 메인 토큰 스트리밍
                    async for chunk in token_stream:
                        nonlocal chunk_count, token_count
                        chunk_count += 1
                        
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
                    
                except Exception as stream_error:
                    logger.error(f"스트리밍 처리 오류: {stream_error}")
                    yield {
                        "type": "error",
                        "content": f"스트리밍 오류: {str(stream_error)}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                logger.info(f"📊 스트리밍 완료 - 총 chunk: {chunk_count}, 토큰: {token_count}")
            
            # **✅ 단순화된 스트리밍 방식**
            try:
                logger.info("🔍 스트리밍 시작 - stream_mode='messages'")
                
                async for result_chunk in merge_streams():
                    # ✅ 최종 응답 캐시
                    if result_chunk.get("type") == "token":
                        if final_response is None:
                            final_response = ""
                        final_response += result_chunk.get("content", "")
                    
                    yield result_chunk
                
                logger.info(f"📝 PostgresSaver를 통해 대화 상태 자동 저장됨 (thread_id: {thread_id})")
            
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


