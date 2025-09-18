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
from src.session.service import get_session_service

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
            await get_container()
            
            # SQL Agent 그래프 생성
            self._agent_graph = await create_sql_agent_graph()
            
            # 세션 서비스 초기화
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
        """질문 처리 (LangGraph 공식 실시간 토큰 스트리밍 + 디버깅)"""
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
        
            # **LangGraph 공식 방식: stream_mode="messages"**
            try:
                logger.info("🔍 스트리밍 시작 - stream_mode='messages'")
                
                async for chunk in self._agent_graph.astream(
                    initial_state,
                    config=config,
                    stream_mode="messages"  # ✅ 공식 방식
                ):
                    chunk_count += 1
                    
                    # # **핵심 디버깅: chunk 구조 완전 분석**
                    # logger.info(f"📦 Chunk #{chunk_count}")
                    # logger.info(f"   Type: {type(chunk)}")
                    # logger.info(f"   Value: {chunk}")
                    # logger.info(f"   Has 'content': {hasattr(chunk, 'content') if hasattr(chunk, '__dict__') else 'N/A'}")
                    # logger.info(f"   Has 'type': {hasattr(chunk, 'type') if hasattr(chunk, '__dict__') else 'N/A'}")
                    
                    # if hasattr(chunk, '__dict__'):
                    #     logger.info(f"   Attributes: {list(chunk.__dict__.keys())}")
                    # elif isinstance(chunk, dict):
                    #     logger.info(f"   Dict keys: {list(chunk.keys())}")
                    # elif isinstance(chunk, (list, tuple)):
                    #     logger.info(f"   Length: {len(chunk)}")
                    #     if chunk:
                    #         logger.info(f"   First item type: {type(chunk[0])}")
                    
                    # **방법 1: 기존 방식**
                    if hasattr(chunk, 'content') and hasattr(chunk, 'type'):
                        if chunk.type == "ai" and chunk.content:
                            token_count += 1
                            # logger.info(f"🟢 토큰 #{token_count}: '{chunk.content[:50]}...'")
                            
                            yield {
                                "type": "token",
                                "content": chunk.content,
                                "timestamp": datetime.now().isoformat()
                            }
                    
                    # **방법 2: 딕셔너리 형태**
                    elif isinstance(chunk, dict):
                        if chunk.get("type") == "ai" and chunk.get("content"):
                            token_count += 1
                            # logger.info(f"🟢 토큰(dict) #{token_count}: '{chunk.get('content')[:50]}...'")
                            
                            yield {
                                "type": "token",
                                "content": chunk["content"],
                                "timestamp": datetime.now().isoformat()
                            }
                    
                    # **방법 3: 리스트 형태**
                    elif isinstance(chunk, list):
                        # logger.info(f"📝 리스트 처리 중... (길이: {len(chunk)})")
                        for i, message in enumerate(chunk):
                            # logger.info(f"   Item #{i}: {type(message)} - {message}")
                            
                            if (hasattr(message, 'content') and 
                                hasattr(message, 'type') and 
                                message.type == "ai" and 
                                message.content):
                                
                                token_count += 1
                                # logger.info(f"🟢 토큰(list) #{token_count}: '{message.content[:50]}...'")
                                
                                yield {
                                    "type": "token",
                                    "content": message.content,
                                    "timestamp": datetime.now().isoformat()
                                }
                    
                    # **방법 4: 튜플 형태 (공식 예제) - 응답 노드만 필터링**
                    elif isinstance(chunk, tuple) and len(chunk) >= 1:
                        # logger.info(f"🔗 튜플 처리 중... (길이: {len(chunk)})")
                        message = chunk[0] if len(chunk) > 0 else None
                        metadata = chunk[1] if len(chunk) > 1 else None
                        
                        # logger.info(f"   Message: {type(message)} - {message}")
                        # logger.info(f"   Node: {metadata.get('langgraph_node', 'UNKNOWN') if metadata else 'NO_METADATA'}")
                        
                        if message and hasattr(message, 'content'):
                            logger.info(f"   Content: '{message.content[:50]}...'")
                        
                        # ✅ 핵심 수정: response 노드에서만 스트리밍
                        if (message and 
                            hasattr(message, 'content') and 
                            message.content and  
                            message.content.strip() and
                            metadata and
                            metadata.get('langgraph_node') == 'response'):  # 🔑 응답 노드만
                            
                            token_count += 1
                            # logger.info(f"🟢 토큰(response) #{token_count}: '{message.content}'")
                            
                            yield {
                                "type": "token",
                                "content": message.content,
                                "timestamp": datetime.now().isoformat()
                            }
                        
                        # 다른 노드 정보는 상태 업데이트로
                        elif metadata and metadata.get('langgraph_node'):
                            node_name = metadata.get('langgraph_node')
                            # logger.info(f"📍 노드 업데이트: {node_name}")
                            
                            yield {
                                "type": "node_update",
                                "node": node_name,
                                "content": f"🔄 {node_name} 실행 중...",
                                "timestamp": datetime.now().isoformat()
                            }
                    
                    # **예상치 못한 형태**
                    else:
                        logger.warning(f"⚠️ 예상치 못한 chunk 형태: {type(chunk)}")
                
                logger.info(f"📊 스트리밍 완료 - 총 chunk: {chunk_count}, 토큰: {token_count}")
        
            except Exception as stream_error:
                logger.error(f"❌ 스트리밍 오류: {stream_error}")
                logger.error(f"   오류 타입: {type(stream_error)}")
                
                # **Fallback 시도**
                logger.info("🔄 Fallback: ainvoke 시도")
                try:
                    result = await self._agent_graph.ainvoke(initial_state, config=config)
                    logger.info(f"📥 Fallback 결과: {type(result)}")
                    logger.info(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    
                    if "messages" in result:
                        logger.info(f"   Messages 개수: {len(result['messages'])}")
                        for i, message in enumerate(result["messages"]):
                            logger.info(f"   Message #{i}: {type(message)} - {getattr(message, 'type', 'NO_TYPE')}")
                        
                        for message in reversed(result["messages"]):
                            if (hasattr(message, 'type') and 
                                message.type == "ai" and 
                                message.content):
                                
                                logger.info(f"🟢 Fallback 응답: '{message.content[:100]}...'")
                                
                                # 전체 응답을 토큰별로 스트리밍
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
