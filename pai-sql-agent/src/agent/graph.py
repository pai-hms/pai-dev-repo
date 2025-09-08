"""
LangGraph 그래프 정의
에이전트의 워크플로우를 정의하고 관리
"""
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph

from src.agent.nodes import (
    analyze_question, execute_tools, generate_response, 
    should_continue, create_agent_state
)
from src.agent.checkpointer import get_postgres_checkpointer


logger = logging.getLogger(__name__)


class SQLAgentGraph:
    """SQL 에이전트 그래프"""
    
    def __init__(self, enable_checkpointer: bool = True):
        self.enable_checkpointer = enable_checkpointer
        self._compiled_graph: Optional[CompiledGraph] = None
    
    def _create_graph(self) -> StateGraph:
        """그래프 생성"""
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
        
        return workflow
    
    async def get_compiled_graph(self) -> CompiledGraph:
        """컴파일된 그래프 반환"""
        if self._compiled_graph is None:
            workflow = self._create_graph()
            
            if self.enable_checkpointer:
                # PostgreSQL 체크포인터 사용
                checkpointer = await get_postgres_checkpointer()
                self._compiled_graph = workflow.compile(checkpointer=checkpointer)
            else:
                self._compiled_graph = workflow.compile()
        
        return self._compiled_graph
    
    async def invoke_query(
        self, 
        question: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """쿼리 실행 (단일 응답)"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 그래프 실행
            graph = await self.get_compiled_graph()
            result = await graph.ainvoke(initial_state, config=config)
            
            return result
            
        except Exception as e:
            logger.error(f"쿼리 실행 중 오류: {str(e)}")
            return {
                "error_message": f"쿼리 실행 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True,
                "messages": []
            }
    
    async def stream_query(
        self, 
        question: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """쿼리 실행 (스트리밍)"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 그래프 스트리밍 실행
            graph = await self.get_compiled_graph()
            
            async for chunk in graph.astream(initial_state, config=config):
                yield chunk
                
        except Exception as e:
            logger.error(f"스트리밍 쿼리 실행 중 오류: {str(e)}")
            yield {
                "error_message": f"스트리밍 실행 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True,
                "messages": []
            }
    
    async def stream_messages(
        self, 
        question: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """메시지 단위 스트리밍"""
        try:
            # 초기 상태 생성
            initial_state = create_agent_state(question).__dict__
            
            # 그래프 스트리밍 실행
            graph = await self.get_compiled_graph()
            
            async for chunk in graph.astream(
                initial_state, 
                config=config,
                stream_mode="messages"
            ):
                # 메시지 청크 처리
                if isinstance(chunk, (list, tuple)) and len(chunk) > 0:
                    message = chunk[0]
                    if hasattr(message, 'content'):
                        # AI 메시지의 컨텐츠만 스트리밍
                        if hasattr(message, 'type') and message.type == 'ai':
                            if hasattr(message.content, '__iter__') and not isinstance(message.content, str):
                                # 청크 단위 컨텐츠
                                for content_chunk in message.content:
                                    if hasattr(content_chunk, 'text'):
                                        yield content_chunk.text
                                    elif isinstance(content_chunk, str):
                                        yield content_chunk
                            else:
                                # 전체 컨텐츠
                                yield str(message.content)
                
        except Exception as e:
            logger.error(f"메시지 스트리밍 중 오류: {str(e)}")
            yield f"오류: {str(e)}"


# 전역 그래프 인스턴스
_sql_agent_graph: Optional[SQLAgentGraph] = None


def get_sql_agent_graph(enable_checkpointer: bool = True) -> SQLAgentGraph:
    """SQL 에이전트 그래프 인스턴스 반환"""
    global _sql_agent_graph
    if _sql_agent_graph is None:
        _sql_agent_graph = SQLAgentGraph(enable_checkpointer=enable_checkpointer)
    return _sql_agent_graph


async def create_session_config(session_id: str) -> Dict[str, Any]:
    """세션 설정 생성"""
    return {
        "configurable": {
            "thread_id": session_id
        }
    }