"""
LangGraph 노드 정의
각 노드는 단일 책임을 가지며, 선형원리에 따라 직선적 흐름을 유지
"""
import logging
from typing import Dict, Any, List, Optional, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool

from src.agent.settings import get_agent_config, SYSTEM_PROMPT, HUMAN_PROMPT
from src.agent.tools import AVAILABLE_TOOLS
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class AgentState:
    """에이전트 상태 관리"""
    
    def __init__(self):
        self.messages: List[BaseMessage] = []
        self.current_query: str = ""
        self.sql_results: List[str] = []
        self.iteration_count: int = 0
        self.max_iterations: int = 10
        self.is_complete: bool = False
        self.error_message: Optional[str] = None
        self.used_tools: List[Dict[str, Any]] = []  # 사용된 도구 추적
    
    def add_message(self, message: BaseMessage) -> None:
        """메시지 추가"""
        self.messages.append(message)
    
    def increment_iteration(self) -> None:
        """반복 횟수 증가"""
        self.iteration_count += 1
    
    def should_continue(self) -> bool:
        """계속 진행할지 판단"""
        return (
            not self.is_complete and 
            self.iteration_count < self.max_iterations and 
            not self.error_message
        )


class SQLAgentNodes:
    """SQL 에이전트 노드들"""
    
    def __init__(self):
        self.settings = get_settings()
        self.agent_config = get_agent_config()
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model=self.agent_config.model_name,
            temperature=self.agent_config.temperature,
            max_tokens=self.agent_config.max_tokens,
            openai_api_key=self.settings.openai_api_key,
            streaming=self.agent_config.enable_streaming
        )
        
        # 도구 바인딩
        self.llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
    
    async def analyze_question_node(self, state: AgentState) -> AgentState:
        """질문 분석 노드"""
        try:
            logger.info("질문 분석 시작")
            
            # 시스템 메시지와 사용자 질문 준비
            messages = [
                HumanMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=HUMAN_PROMPT.format(question=state.current_query))
            ]
            
            # LLM 호출
            response = await self.llm_with_tools.ainvoke(messages)
            
            # 응답을 상태에 추가
            state.add_message(response)
            state.increment_iteration()
            
            logger.info("질문 분석 완료")
            return state
            
        except Exception as e:
            logger.error(f"질문 분석 중 오류: {str(e)}")
            state.error_message = f"질문 분석 중 오류가 발생했습니다: {str(e)}"
            return state
    
    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """도구 실행 노드"""
        try:
            # 마지막 메시지에서 도구 호출 확인
            last_message = state.messages[-1] if state.messages else None
            
            if not last_message or not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                # 도구 호출이 없으면 완료로 처리
                state.is_complete = True
                return state
            
            logger.info(f"도구 실행 시작: {len(last_message.tool_calls)}개")
            
            # 각 도구 호출 처리
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
                
                logger.info(f"도구 실행: {tool_name}, 인자: {tool_args}")
                
                # 도구 찾기
                tool = self._find_tool(tool_name)
                if not tool:
                    error_msg = f"도구를 찾을 수 없습니다: {tool_name}"
                    state.add_message(
                        ToolMessage(content=error_msg, tool_call_id=tool_id)
                    )
                    continue
                
                # 도구 실행 시작 로깅
                logger.info(f"🔄 도구 실행 시작: {tool_name} | 파라미터: {tool_args}")
                
                # 도구 실행
                try:
                    # LangChain 도구는 항상 ainvoke 사용
                    result = await tool.ainvoke(tool_args)
                    
                    # 도구 사용 정보 추적
                    tool_info = {
                        "tool_name": tool_name,
                        "tool_function": tool.name,
                        "tool_description": tool.description,
                        "arguments": tool_args,
                        "result_preview": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        "execution_order": len(state.used_tools) + 1,
                        "success": True
                    }
                    state.used_tools.append(tool_info)
                    
                    # SQL 결과인 경우 별도 저장
                    if tool_name == "execute_sql_query":
                        state.sql_results.append(str(result))
                    
                    # 도구 결과를 메시지로 추가
                    state.add_message(
                        ToolMessage(content=str(result), tool_call_id=tool_id)
                    )
                    
                    logger.info(f"✅ 도구 실행 완료: {tool_name} | 결과: 성공")
                    
                except Exception as tool_error:
                    error_msg = f"도구 실행 중 오류: {str(tool_error)}"
                    logger.error(error_msg)
                    
                    # 실패한 도구 정보도 추적
                    tool_info = {
                        "tool_name": tool_name,
                        "tool_function": tool.name,
                        "tool_description": tool.description,
                        "arguments": tool_args,
                        "error_message": error_msg,
                        "execution_order": len(state.used_tools) + 1,
                        "success": False
                    }
                    state.used_tools.append(tool_info)
                    
                    state.add_message(
                        ToolMessage(content=error_msg, tool_call_id=tool_id)
                    )
            
            state.increment_iteration()
            return state
            
        except Exception as e:
            logger.error(f"도구 실행 중 오류: {str(e)}")
            state.error_message = f"도구 실행 중 오류가 발생했습니다: {str(e)}"
            return state
    
    async def generate_response_node(self, state: AgentState) -> AgentState:
        """응답 생성 노드"""
        try:
            logger.info("최종 응답 생성 시작")
            
            # 도구 실행 결과가 있으면 최종 응답 생성
            if state.messages and len(state.messages) > 1:
                # 전체 컨텍스트를 포함한 응답 생성
                response = await self.llm.ainvoke(state.messages)
                state.add_message(response)
            
            state.is_complete = True
            state.increment_iteration()
            
            logger.info("최종 응답 생성 완료")
            return state
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {str(e)}")
            state.error_message = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
            return state
    
    def _find_tool(self, tool_name: str) -> Optional[BaseTool]:
        """도구 이름으로 도구 객체 찾기"""
        for tool in AVAILABLE_TOOLS:
            if tool.name == tool_name:
                return tool
        return None
    
    def should_continue_routing(self, state: AgentState) -> str:
        """라우팅 조건 판단"""
        # 에러가 있으면 종료
        if state.error_message:
            return "end"
        
        # 완료되었으면 종료
        if state.is_complete:
            return "end"
        
        # 최대 반복 횟수 초과시 종료
        if state.iteration_count >= state.max_iterations:
            return "end"
        
        # 마지막 메시지가 도구 호출을 포함하면 도구 실행
        if state.messages:
            last_message = state.messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "execute_tools"
            
            # 도구 메시지 다음엔 응답 생성
            if isinstance(last_message, ToolMessage):
                return "generate_response"
        
        # 첫 번째 분석 후엔 도구 실행 또는 응답 생성
        return "generate_response"


def create_agent_state(question: str) -> AgentState:
    """에이전트 상태 생성"""
    state = AgentState()
    state.current_query = question
    return state


# 노드 함수들 (그래프에서 사용할 래퍼 함수들)
_nodes = SQLAgentNodes()

async def analyze_question(state: Dict[str, Any]) -> Dict[str, Any]:
    """질문 분석 노드 래퍼"""
    agent_state = AgentState()
    agent_state.__dict__.update(state)
    
    result_state = await _nodes.analyze_question_node(agent_state)
    return result_state.__dict__

async def execute_tools(state: Dict[str, Any]) -> Dict[str, Any]:
    """도구 실행 노드 래퍼"""
    agent_state = AgentState()
    agent_state.__dict__.update(state)
    
    result_state = await _nodes.execute_tools_node(agent_state)
    return result_state.__dict__

async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """응답 생성 노드 래퍼"""
    agent_state = AgentState()
    agent_state.__dict__.update(state)
    
    result_state = await _nodes.generate_response_node(agent_state)
    return result_state.__dict__

def should_continue(state: Dict[str, Any]) -> str:
    """라우팅 조건 판단 래퍼"""
    agent_state = AgentState()
    agent_state.__dict__.update(state)
    
    return _nodes.should_continue_routing(agent_state)
