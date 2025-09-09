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


# LangGraph 호환 상태 타입 정의
from typing import TypedDict

class AgentState(TypedDict):
    """
    LangGraph 호환 에이전트 상태 
    딕셔너리 기반으로 완전한 직렬화/역직렬화 지원
    """
    messages: List[BaseMessage]
    current_query: str
    sql_results: List[str]
    iteration_count: int
    max_iterations: int
    is_complete: bool
    error_message: Optional[str]
    used_tools: List[Dict[str, Any]]

def create_agent_state(query: str = "") -> AgentState:
    """새로운 에이전트 상태 생성"""
    return {
        "messages": [],
        "current_query": query,
        "sql_results": [],
        "iteration_count": 0,
        "max_iterations": 10,
        "is_complete": False,
        "error_message": None,
        "used_tools": []
    }


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
        """질문 분석 노드 (딕셔너리 기반)"""
        try:
            logger.info("🔍 질문 분석 시작")
            
            messages = state["messages"].copy()
            current_query = state["current_query"]
            iteration_count = state["iteration_count"]
            
            # 첫 번째 메시지인 경우에만 시스템 프롬프트 추가
            if not messages:
                logger.info("📝 새 대화 시작 - 시스템 프롬프트 추가")
                from src.agent.settings import SYSTEM_PROMPT
                # 시스템 프롬프트를 AI 메시지로 추가 (대화 기록에 포함)
                system_msg = AIMessage(content=SYSTEM_PROMPT)
                messages.append(system_msg)
            
            # 현재 질문을 사용자 메시지로 추가
            if current_query:
                user_msg = HumanMessage(content=current_query)
                messages.append(user_msg)
                logger.info(f"💬 사용자 질문 추가: {current_query[:50]}...")
            
            # LLM 호출
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)
            
            logger.info("✅ 질문 분석 완료")
            
            # 딕셔너리 상태 업데이트하여 반환
            return {
                **state,
                "messages": messages,
                "iteration_count": iteration_count + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 질문 분석 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"질문 분석 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """도구 실행 노드 (딕셔너리 기반)"""
        try:
            messages = state["messages"].copy()
            sql_results = state["sql_results"].copy()
            used_tools = state["used_tools"].copy()
            
            # 마지막 메시지에서 도구 호출 확인
            last_message = messages[-1] if messages else None
            
            if not last_message or not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                # 도구 호출이 없으면 완료로 처리
                logger.info("ℹ️ 도구 호출 없음 - 완료 처리")
                return {
                    **state,
                    "is_complete": True
                }
            
            logger.info(f"🔧 도구 실행 시작: {len(last_message.tool_calls)}개")
            
            # 각 도구 호출 처리
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
                
                logger.info(f"⚙️ 도구 실행: {tool_name}, 인자: {tool_args}")
                
                # 도구 찾기
                tool = self._find_tool(tool_name)
                if not tool:
                    error_msg = f"도구를 찾을 수 없습니다: {tool_name}"
                    messages.append(
                        ToolMessage(content=error_msg, tool_call_id=tool_id)
                    )
                    continue
                
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
                        "execution_order": len(used_tools) + 1,
                        "success": True
                    }
                    used_tools.append(tool_info)
                    
                    # SQL 결과인 경우 별도 저장
                    if tool_name == "execute_sql_query":
                        sql_results.append(str(result))
                    
                    # 도구 결과를 메시지로 추가
                    messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_id)
                    )
                    
                    logger.info(f"✅ 도구 실행 완료: {tool_name}")
                    
                except Exception as tool_error:
                    error_msg = f"도구 실행 중 오류: {str(tool_error)}"
                    logger.error(f"❌ {error_msg}")
                    
                    # 실패한 도구 정보도 추적
                    tool_info = {
                        "tool_name": tool_name,
                        "tool_function": tool.name,
                        "tool_description": tool.description,
                        "arguments": tool_args,
                        "error_message": error_msg,
                        "execution_order": len(used_tools) + 1,
                        "success": False
                    }
                    used_tools.append(tool_info)
                    
                    messages.append(
                        ToolMessage(content=error_msg, tool_call_id=tool_id)
                    )
            
            logger.info("🔧 모든 도구 실행 완료")
            
            # 딕셔너리 상태 업데이트하여 반환
            return {
                **state,
                "messages": messages,
                "sql_results": sql_results,
                "used_tools": used_tools,
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 도구 실행 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"도구 실행 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    async def generate_response_node(self, state: AgentState) -> AgentState:
        """응답 생성 노드 (딕셔너리 기반)"""
        try:
            logger.info("🎯 최종 응답 생성 시작")
            
            messages = state["messages"].copy()
            
            # 도구 실행 결과가 있으면 최종 응답 생성
            if messages and len(messages) > 1:
                # 전체 컨텍스트를 포함한 응답 생성
                response = await self.llm.ainvoke(messages)
                messages.append(response)
                logger.info("✅ 최종 응답 생성 완료")
            else:
                # 메시지가 없는 경우 기본 응답
                default_response = AIMessage(content="죄송합니다. 적절한 응답을 생성할 수 없습니다.")
                messages.append(default_response)
                logger.warning("⚠️ 기본 응답으로 처리")
            
            # 딕셔너리 상태 업데이트하여 반환
            return {
                **state,
                "messages": messages,
                "is_complete": True,
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 응답 생성 중 오류: {str(e)}")
            error_response = AIMessage(content=f"응답 생성 중 오류가 발생했습니다: {str(e)}")
            return {
                **state,
                "messages": state["messages"] + [error_response],
                "error_message": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    def _find_tool(self, tool_name: str) -> Optional[BaseTool]:
        """도구 이름으로 도구 객체 찾기"""
        for tool in AVAILABLE_TOOLS:
            if tool.name == tool_name:
                return tool
        return None
    
    def should_continue_routing(self, state: AgentState) -> str:
        """라우팅 조건 판단 (딕셔너리 기반)"""
        # 에러가 있으면 종료
        if state.get("error_message"):
            return "end"
        
        # 완료되었으면 종료
        if state.get("is_complete"):
            return "end"
        
        # 최대 반복 횟수 초과시 종료
        if state.get("iteration_count", 0) >= state.get("max_iterations", 10):
            return "end"
        
        # 마지막 메시지가 도구 호출을 포함하면 도구 실행
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "execute_tools"
            
            # 도구 메시지 다음엔 응답 생성
            if isinstance(last_message, ToolMessage):
                return "generate_response"
        
        # 첫 번째 분석 후엔 도구 실행 또는 응답 생성
        return "generate_response"


# 노드 함수들 (LangGraph 딕셔너리 기반 래퍼)
_nodes = SQLAgentNodes()

async def analyze_question(state: Dict[str, Any]) -> Dict[str, Any]:
    """질문 분석 노드 래퍼 (딕셔너리 기반)"""
    logger.info("🔄 analyze_question 래퍼 호출")
    try:
        # 딕셔너리 상태를 AgentState 형식으로 변환
        agent_state: AgentState = {
            "messages": state.get("messages", []),
            "current_query": state.get("current_query", ""),
            "sql_results": state.get("sql_results", []),
            "iteration_count": state.get("iteration_count", 0),
            "max_iterations": state.get("max_iterations", 10),
            "is_complete": state.get("is_complete", False),
            "error_message": state.get("error_message"),
            "used_tools": state.get("used_tools", [])
        }
        
        result_state = await _nodes.analyze_question_node(agent_state)
        logger.info("✅ analyze_question 래퍼 완료")
        return result_state
        
    except Exception as e:
        logger.error(f"❌ analyze_question 래퍼 오류: {e}")
        return {
            **state,
            "error_message": f"질문 분석 래퍼 오류: {str(e)}",
            "is_complete": True
        }

async def execute_tools(state: Dict[str, Any]) -> Dict[str, Any]:
    """도구 실행 노드 래퍼 (딕셔너리 기반)"""
    logger.info("🔄 execute_tools 래퍼 호출")
    try:
        # 딕셔너리 상태를 AgentState 형식으로 변환
        agent_state: AgentState = {
            "messages": state.get("messages", []),
            "current_query": state.get("current_query", ""),
            "sql_results": state.get("sql_results", []),
            "iteration_count": state.get("iteration_count", 0),
            "max_iterations": state.get("max_iterations", 10),
            "is_complete": state.get("is_complete", False),
            "error_message": state.get("error_message"),
            "used_tools": state.get("used_tools", [])
        }
        
        result_state = await _nodes.execute_tools_node(agent_state)
        logger.info("✅ execute_tools 래퍼 완료")
        return result_state
        
    except Exception as e:
        logger.error(f"❌ execute_tools 래퍼 오류: {e}")
        return {
            **state,
            "error_message": f"도구 실행 래퍼 오류: {str(e)}",
            "is_complete": True
        }

async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """응답 생성 노드 래퍼 (딕셔너리 기반)"""
    logger.info("🔄 generate_response 래퍼 호출")
    try:
        # 딕셔너리 상태를 AgentState 형식으로 변환
        agent_state: AgentState = {
            "messages": state.get("messages", []),
            "current_query": state.get("current_query", ""),
            "sql_results": state.get("sql_results", []),
            "iteration_count": state.get("iteration_count", 0),
            "max_iterations": state.get("max_iterations", 10),
            "is_complete": state.get("is_complete", False),
            "error_message": state.get("error_message"),
            "used_tools": state.get("used_tools", [])
        }
        
        result_state = await _nodes.generate_response_node(agent_state)
        logger.info("✅ generate_response 래퍼 완료")
        return result_state
        
    except Exception as e:
        logger.error(f"❌ generate_response 래퍼 오류: {e}")
        return {
            **state,
            "error_message": f"응답 생성 래퍼 오류: {str(e)}",
            "is_complete": True
        }

def should_continue(state: Dict[str, Any]) -> str:
    """라우팅 조건 판단 래퍼 (딕셔너리 기반)"""
    logger.info("🔄 should_continue 래퍼 호출")
    try:
        # 딕셔너리 상태를 AgentState 형식으로 변환
        agent_state: AgentState = {
            "messages": state.get("messages", []),
            "current_query": state.get("current_query", ""),
            "sql_results": state.get("sql_results", []),
            "iteration_count": state.get("iteration_count", 0),
            "max_iterations": state.get("max_iterations", 10),
            "is_complete": state.get("is_complete", False),
            "error_message": state.get("error_message"),
            "used_tools": state.get("used_tools", [])
        }
        
        result = _nodes.should_continue_routing(agent_state)
        logger.info(f"✅ should_continue 래퍼 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ should_continue 래퍼 오류: {e}")
        return "end"
