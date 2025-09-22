"""
SQL Agent 서비스 - DI 패턴 적용
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph

from .domain import QueryParam, AgentResponse, ToolCallInfo, ToolResult
from .nodes import create_initial_state

logger = logging.getLogger(__name__)


class SQLAgentService:
    """SQL Agent 서비스 - DI 패턴 적용"""
    
    def __init__(self, workflow: Optional[CompiledStateGraph] = None):
        """의존성 주입 생성자"""
        self._agent_graph = workflow
        self._initialized = False
    
    def set_workflow(self, workflow: CompiledStateGraph):
        """워크플로우 설정 (DI용)"""
        self._agent_graph = workflow
        self._initialized = True
    
    async def process_query_stream(
        self,
        question: str,
        query_param: QueryParam
    ) -> AsyncGenerator[str, None]:
        """스트리밍 쿼리 처리 - 도메인 객체 사용"""
        
        logger.info(f"스트리밍 쿼리 처리 시작: {question[:50]}...")
        
        # 워크플로우 지연 로딩
        if not self._agent_graph:
            logger.info("워크플로우 지연 로딩 시작")
            from .graph import create_sql_agent_graph
            self._agent_graph = await create_sql_agent_graph()
            self._initialized = True
            logger.info("워크플로우 지연 로딩 완료")
        
        logger.info(f"서비스 초기화 상태: {self._initialized}")
        logger.info(f"워크플로우 존재 여부: {self._agent_graph is not None}")
        
        try:
            # 시작 신호
            start_response = AgentResponse(
                content="SQL 분석을 시작합니다...",
                session_id=query_param.session_id,
                response_type="start"
            )
            yield json.dumps(start_response.to_dict(), ensure_ascii=False) + '\n'
            
            # 도구 호출 상태 관리
            has_tool_calls = False
            
            logger.info("LangGraph 스트리밍 시작")
            logger.info(f"세션 ID: {query_param.session_id}")
            
            # LangGraph 스트리밍 실행
            stream_count = 0
            async for state_map in self._agent_graph.astream(
                {"messages": [HumanMessage(content=question)]},
                config={
                    "configurable": {"thread_id": query_param.session_id},
                    "recursion_limit": 50
                },
                stream_mode="messages",
            ):
                stream_count += 1
                logger.info(f"스트림 이벤트 #{stream_count} 수신: {type(state_map)}")
                message, metadata = state_map
                
                # AI 메시지 처리
                if isinstance(message, AIMessageChunk):
                    # 도구 호출 감지
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        has_tool_calls = True
                        
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.get('name')
                            if tool_name and tool_name.strip():
                                # 도구 호출 정보 생성
                                tool_info = ToolCallInfo(
                                    tool_name=tool_name,
                                    session_id=query_param.session_id,
                                    message_id=message.id,
                                    args=tool_call.get('args', {})
                                )
                                yield json.dumps(tool_info.to_dict(), ensure_ascii=False) + '\n'
                    
                    # 일반 메시지 내용
                    if message.content and not has_tool_calls:
                        response = AgentResponse(
                            content=message.content,
                            session_id=query_param.session_id,
                            message_id=message.id
                        )
                        yield json.dumps(response.to_dict(), ensure_ascii=False) + '\n'
                
                # 도구 실행 결과 처리
                elif isinstance(message, ToolMessage):
                    tool_result = ToolResult(
                        tool_name=message.name,
                        content=message.content,
                        session_id=query_param.session_id,
                        message_id=message.id
                    )
                    yield json.dumps(tool_result.to_dict(), ensure_ascii=False) + '\n'
                    
                    # 상태 초기화
                    has_tool_calls = False
            
            # 완료 신호
            complete_response = AgentResponse(
                content="SQL 분석이 완료되었습니다.",
                session_id=query_param.session_id,
                response_type="complete"
            )
            yield json.dumps(complete_response.to_dict(), ensure_ascii=False) + '\n'
            
        except Exception as e:
            logger.error(f"스트리밍 쿼리 처리 오류: {e}")
            error_response = AgentResponse(
                content=f"처리 중 오류가 발생했습니다: {str(e)}",
                session_id=query_param.session_id,
                response_type="error"
            )
            yield json.dumps(error_response.to_dict(), ensure_ascii=False) + '\n'


# 전역 서비스 인스턴스 (하위 호환성을 위해 유지)
_sql_agent_service: Optional[SQLAgentService] = None
_service_lock = asyncio.Lock()


async def get_sql_agent_service() -> SQLAgentService:
    """SQL Agent 서비스 싱글톤 인스턴스 반환 (하위 호환성)"""
    global _sql_agent_service
    
    if _sql_agent_service is None:
        async with _service_lock:
            if _sql_agent_service is None:
                from .container import get_agent_container
                container = await get_agent_container()
                _sql_agent_service = await container.get("agent_service")
    
    return _sql_agent_service