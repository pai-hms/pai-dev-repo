"""
LangGraph 노드 정의 + 상태 정의
Chain invoke 방식을 사용한 깔끔한 구조
"""
import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool

from src.agent.settings import get_agent_config
from src.agent.prompt import SYSTEM_PROMPT
from src.agent.tools import AVAILABLE_TOOLS
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# ===== 상태 정의 =====
class AgentState(TypedDict):
    """SQL Agent 상태"""
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

# ===== 노드 로직 =====
class SQLAgentNode:
    """SQL Agent의 메인 노드 - Chain invoke 방식 사용"""
    
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
        
        # Chain 생성
        self.analysis_chain = self._create_analysis_chain()
        self.response_chain = self._create_response_chain()
    
    def _create_analysis_chain(self):
        """분석용 체인 생성 (도구 포함)"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])
        
        llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
        return prompt | llm_with_tools
    
    def _create_response_chain(self):
        """응답 생성용 체인 생성 (도구 없음)"""
        prompt = ChatPromptTemplate.from_messages([
            ("placeholder", "{messages}"),
        ])
        
        return prompt | self.llm
    
    def _clean_incomplete_tool_calls(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """불완전한 tool call 메시지들을 정리"""
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
                    logger.warning(f"⚠️ 불완전한 tool call 발견 - 건너뛰기: {tool_call_ids - found_tool_messages}")
                    i = j
            else:
                # 일반 메시지는 그대로 추가
                cleaned_messages.append(message)
                i += 1
        
        return cleaned_messages
    
    async def analyze_question(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """질문 분석 노드 - Chain invoke 방식"""
        try:
            logger.info("🔍 질문 분석 시작")
            
            messages = state["messages"].copy()
            current_query = state["current_query"]
            
            # 메시지 상태 검증 및 정리
            messages = self._clean_incomplete_tool_calls(messages)
            
            # 새로운 질문이 있으면 항상 추가 (동일한 질문이라도 새로운 응답 생성)
            if current_query:
                user_msg = HumanMessage(
                    content=current_query,
                    additional_kwargs={"timestamp": datetime.now().isoformat()}
                )
                messages.append(user_msg)
                logger.info(f"💬 사용자 질문 추가: {current_query[:50]}...")
            
            # Chain 호출로 분석 수행
            response = await self.analysis_chain.ainvoke({"messages": messages}, config=config)
            messages.append(response)
            
            logger.info("✅ 질문 분석 완료")
            
            return {
                **state,
                "messages": messages,
                "iteration_count": state["iteration_count"] + 1
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
    
    async def generate_response(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """응답 생성 노드 - Chain invoke 방식"""
        try:
            logger.info("🎯 최종 응답 생성 시작")
            
            messages = state["messages"].copy()
            
            # 메시지 상태 검증 및 정리
            messages = self._clean_incomplete_tool_calls(messages)
            
            if messages and len(messages) > 1:
                # Chain 호출로 응답 생성
                response = await self.response_chain.ainvoke({"messages": messages}, config=config)
                messages.append(response)
                logger.info("✅ 최종 응답 생성 완료")
            else:
                default_response = AIMessage(content="죄송합니다. 적절한 응답을 생성할 수 없습니다.")
                messages.append(default_response)
                logger.warning("⚠️ 기본 응답으로 처리")
            
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
    
    def should_continue_routing(self, state: Dict[str, Any]) -> str:
        """라우팅 조건 판단 (딕셔너리 기반)"""
        # 에러가 있으면 종료
        if state.get("error_message"):
            logger.info("🛑 에러로 인한 종료")
            return "end"
        
        # 완료되었으면 종료
        if state.get("is_complete"):
            logger.info("✅ 완료로 인한 종료")
            return "end"
        
        # 최대 반복 횟수 초과시 종료
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 10)
        if iteration_count >= max_iterations:
            logger.info(f"🔄 최대 반복 횟수 초과 ({iteration_count}/{max_iterations})")
            return "end"
        
        # 메시지 상태 분석
        messages = state.get("messages", [])
        logger.info(f"📋 메시지 개수: {len(messages)}")
        
        if messages:
            last_message = messages[-1]
            logger.info(f"📝 마지막 메시지 타입: {type(last_message).__name__}")
            
            # AI 메시지에 도구 호출이 있는 경우
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                logger.info(f"🔧 도구 호출 발견: {len(last_message.tool_calls)}개")
                return "execute_tools"
            
            # 도구 메시지 다음엔 응답 생성
            if isinstance(last_message, ToolMessage):
                logger.info("🛠️ 도구 메시지 후 응답 생성")
                return "generate_response"
            
            # AI 메시지이지만 도구 호출이 없는 경우 - 최종 응답으로 처리
            if isinstance(last_message, AIMessage):
                logger.info("🤖 AI 응답 완료 - 종료")
                return "end"
        
        # 기본적으로 응답 생성
        logger.info("📝 기본 응답 생성")
        return "generate_response"


# ===== 노드 인스턴스 (싱글톤) =====
_sql_agent_node = SQLAgentNode()

# ===== 래퍼 함수들 (기존 호환성 유지) =====
async def analyze_question(state: Dict[str, Any]) -> Dict[str, Any]:
    """질문 분석 노드 래퍼"""
    return await _sql_agent_node.analyze_question(state)

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
        
        result_state = await _sql_agent_node.execute_tools_node(agent_state)
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
    """응답 생성 노드 래퍼"""
    return await _sql_agent_node.generate_response(state)

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
        
        result = _sql_agent_node.should_continue_routing(agent_state)
        logger.info(f"✅ should_continue 래퍼 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ should_continue 래퍼 오류: {e}")
        return "end"
