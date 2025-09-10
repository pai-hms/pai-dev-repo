"""
SQL Agent 서비스 - 사용자 인터페이스
"""
import logging
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, AIMessageChunk
from langgraph.graph.state import CompiledStateGraph

from src.agent.nodes import AgentState, create_agent_state
from src.agent.graph import create_sql_agent_graph

logger = logging.getLogger(__name__)

def serialize_message_for_checkpoint(message: AnyMessage) -> dict:
    """메시지를 체크포인트 저장용으로 직렬화합니다."""
    if isinstance(message, HumanMessage):
        return {
            "type": "human",
            "content": message.content,
            "additional_kwargs": message.additional_kwargs or {},
            "name": message.name,
            "id": message.id,
        }
    else:
        # 다른 메시지 타입은 model_dump() 사용
        return message.model_dump()

class SQLAgentService:
    """SQL Agent 서비스 - 깔끔한 인터페이스"""
    
    def __init__(self, enable_checkpointer: bool = True):
        self.enable_checkpointer = enable_checkpointer
        self._agent = None
    
    async def _get_agent(self):
        """지연 초기화로 에이전트 생성"""
        if self._agent is None:
            self._agent = await create_sql_agent_graph(self.enable_checkpointer)
        return self._agent
    
    async def invoke_query(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """단일 응답 실행"""
        try:
            logger.info(f"🚀 쿼리 실행 시작: {question[:50]}...")
            
            # 에이전트 가져오기
            agent = await self._get_agent()
            
            # 설정 생성
            config = self._create_config(session_id) if session_id else None
            
            # 초기 상태 생성
            initial_state = await self._get_initial_state(question, session_id, config)
            
            # 그래프 실행
            result = await agent.ainvoke(initial_state, config=config)
            
            logger.info("✅ 쿼리 실행 완료")
            return result
            
        except Exception as e:
            logger.error(f"❌ 쿼리 실행 중 오류: {str(e)}")
            return self._create_error_response(question, str(e))
    
    async def stream_query(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 응답 실행"""
        try:
            logger.info(f"🚀 스트리밍 쿼리 시작: {question[:50]}...")
            
            agent = await self._get_agent()
            config = self._create_config(session_id) if session_id else None
            initial_state = await self._get_initial_state(question, session_id, config)
            
            async for stream_mode, chunk in agent.astream(
                initial_state,
                config=config,
                stream_mode=["messages", "updates"]
            ):
                if stream_mode == "messages":
                    message, metadata = chunk
                    if isinstance(message, (AIMessage, AIMessageChunk)) and message.content:
                        yield {
                            "type": "token",
                            "content": message.content,
                            "metadata": metadata
                        }
                elif stream_mode == "updates":
                    # 도구 실행 업데이트
                    if "execute_tools" in chunk:
                        for message in chunk["execute_tools"]["messages"]:
                            if isinstance(message, HumanMessage):
                                continue
                            yield {
                                "type": "tool_result",
                                "content": message
                            }
                    elif "analyze_question" in chunk:
                        for message in chunk["analyze_question"]["messages"]:
                            if hasattr(message, 'tool_calls') and message.tool_calls:
                                yield {
                                    "type": "tool_call",
                                    "content": message
                                }
                        
        except Exception as e:
            logger.error(f"❌ 스트리밍 실행 중 오류: {str(e)}")
            yield {
                "type": "error",
                "content": f"스트리밍 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def get_chat_history(self, session_id: str) -> List[AnyMessage]:
        """채팅 기록 조회"""
        if not self.enable_checkpointer:
            return []
        
        try:
            agent = await self._get_agent()
            config = self._create_config(session_id)
            state = await agent.aget_state(config)
            return state.values.get("messages", [])
        except Exception as e:
            logger.error(f"채팅 기록 조회 중 오류: {str(e)}")
            return []
    
    async def update_message_feedback(
        self,
        session_id: str,
        checkpoint_id: str,
        like: bool | None,
    ) -> None:
        """특정 메시지에 피드백 기록"""
        if not self.enable_checkpointer:
            return
            
        try:
            agent = await self._get_agent()
            config = self._create_config(session_id)

            state = await agent.aget_state(config)
            messages: List[AnyMessage] = state.values.get("messages", [])

            target = next(
                (m for m in messages if getattr(m, "id", None) == checkpoint_id), None
            )
            
            if target:
                patched = target.model_copy(
                    update={
                        "additional_kwargs": {
                            **(target.additional_kwargs or {}),
                            "like": like,
                        }
                    },
                    deep=True,
                )

                # 상태 업데이트 시 직렬화 가능한 형태로 변환
                serialized_message = serialize_message_for_checkpoint(patched)
                await agent.aupdate_state(
                    config,
                    {"messages": [serialized_message]}
                )
        except Exception as e:
            logger.error(f"메시지 피드백 업데이트 중 오류: {str(e)}")
    
    def _create_config(self, session_id: str) -> Dict[str, Any]:
        """실행 설정 생성"""
        return {"configurable": {"thread_id": session_id}}
    
    async def _get_initial_state(
        self, 
        question: str, 
        session_id: Optional[str], 
        config: Optional[Dict[str, Any]]
    ) -> AgentState:
        """초기 상태 생성 또는 복원"""
        if self.enable_checkpointer and session_id and config:
            try:
                agent = await self._get_agent()
                existing_state = await agent.aget_state(config)
                if existing_state and existing_state.values:
                    # 기존 상태에 새 질문 추가
                    initial_state = existing_state.values.copy()
                    initial_state["current_query"] = question
                    
                    # 새로운 질문이므로 상태 리셋
                    initial_state["is_complete"] = False
                    initial_state["error_message"] = None
                    initial_state["current_step"] = "analyze_question"
                    
                    # 고도화된 워크플로우 상태 리셋
                    initial_state["requirements"] = None
                    initial_state["analysis_plan"] = None
                    initial_state["proposed_queries"] = []
                    initial_state["validated_query"] = None
                    initial_state["execution_errors"] = []
                    initial_state["result_quality_score"] = None
                    initial_state["data_insights"] = None
                    initial_state["recommendations"] = None
                    
                    # 불완전한 tool call 상태 정리
                    messages = initial_state.get("messages", [])
                    if messages:
                        initial_state["messages"] = self._clean_incomplete_tool_calls(messages)
                    
                    logger.info(f"💾 기존 대화 기록 로드 완료 (상태 리셋)")
                    return initial_state
            except Exception as e:
                logger.warning(f"⚠️ 기존 상태 로드 실패: {str(e)}")
        
        # 새 상태 생성
        return create_agent_state(question)
    
    def _clean_incomplete_tool_calls(self, messages: List[AnyMessage]) -> List[AnyMessage]:
        """불완전한 tool call 메시지들을 정리 (서비스 레벨)"""
        from langchain_core.messages import AIMessage, ToolMessage
        
        cleaned_messages = []
        i = 0
        
        while i < len(messages):
            message = messages[i]
            
            # AI 메시지에 tool_calls가 있는 경우
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                # 다음 메시지들이 모든 tool_calls에 대한 ToolMessage인지 확인
                tool_call_ids = {call['id'] for call in message.tool_calls}
                j = i + 1
                found_tool_messages = set()
                
                # 연속된 ToolMessage들을 찾아서 매칭되는지 확인
                while j < len(messages) and isinstance(messages[j], ToolMessage):
                    if messages[j].tool_call_id in tool_call_ids:
                        found_tool_messages.add(messages[j].tool_call_id)
                    j += 1
                
                # 모든 tool_calls에 대한 응답이 있는 경우에만 추가
                if tool_call_ids == found_tool_messages:
                    # AI 메시지와 해당하는 모든 ToolMessage들을 추가
                    cleaned_messages.append(message)
                    for k in range(i + 1, j):
                        if isinstance(messages[k], ToolMessage) and messages[k].tool_call_id in tool_call_ids:
                            cleaned_messages.append(messages[k])
                    i = j
                else:
                    # 불완전한 tool call이므로 건너뛰기
                    logger.warning(f"⚠️ 불완전한 tool call 상태 정리: {tool_call_ids - found_tool_messages}")
                    i = j
            else:
                # 일반 메시지는 그대로 추가
                cleaned_messages.append(message)
                i += 1
        
        return cleaned_messages
    
    def _create_error_response(self, question: str, error: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            "error_message": f"쿼리 실행 중 오류가 발생했습니다: {error}",
            "is_complete": True,
            "messages": [],
            "current_query": question,
            "sql_results": [],
            "used_tools": [],
            "iteration_count": 0,
            "max_iterations": 10
        }

# ===== 전역 서비스 인스턴스 (싱글톤) =====
_sql_agent_service: Optional[SQLAgentService] = None

def get_sql_agent_service(enable_checkpointer: bool = True) -> SQLAgentService:
    """SQL Agent 서비스 인스턴스 반환"""
    global _sql_agent_service
    if _sql_agent_service is None:
        _sql_agent_service = SQLAgentService(enable_checkpointer=enable_checkpointer)
    return _sql_agent_service

# 하위 호환성을 위한 함수들
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
