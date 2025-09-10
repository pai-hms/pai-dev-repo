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
    """SQL Agent 상태 - 고도화된 워크플로우용"""
    messages: List[BaseMessage]
    current_query: str
    
    # 분석 단계
    requirements: Optional[str]  # 요구사항 분석 결과
    analysis_plan: Optional[str]  # 분석 전략
    
    # 쿼리 단계
    proposed_queries: List[str]  # 제안된 SQL 쿼리들
    validated_query: Optional[str]  # 검증된 최종 쿼리
    
    # 실행 및 결과 단계
    sql_results: List[str]
    execution_errors: List[str]  # SQL 실행 오류들
    result_quality_score: Optional[float]  # 결과 품질 점수
    
    # 분석 단계
    data_insights: Optional[str]  # 데이터 인사이트
    recommendations: Optional[str]  # 추천사항
    
    # 제어 플래그
    iteration_count: int
    max_iterations: int
    is_complete: bool
    error_message: Optional[str]
    used_tools: List[Dict[str, Any]]
    current_step: str  # 현재 진행 단계

def create_agent_state(query: str = "") -> AgentState:
    """새로운 에이전트 상태 생성 - 고도화된 워크플로우용"""
    return {
        "messages": [],
        "current_query": query,
        
        # 분석 단계
        "requirements": None,
        "analysis_plan": None,
        
        # 쿼리 단계
        "proposed_queries": [],
        "validated_query": None,
        
        # 실행 및 결과 단계
        "sql_results": [],
        "execution_errors": [],
        "result_quality_score": None,
        
        # 분석 단계
        "data_insights": None,
        "recommendations": None,
        
        # 제어 플래그
        "iteration_count": 0,
        "max_iterations": 10,
        "is_complete": False,
        "error_message": None,
        "used_tools": [],
        "current_step": "analyze_question"
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
        
        # Chain 생성 - 기존
        self.analysis_chain = self._create_analysis_chain()
        self.response_chain = self._create_response_chain()
        
        # 새로운 단계별 Chain 생성
        self.plan_chain = self._create_plan_chain()
        self.build_query_chain = self._create_build_query_chain()
        self.validate_chain = self._create_validate_chain()
        self.analyze_data_chain = self._create_analyze_data_chain()
        self.final_response_chain = self._create_final_response_chain()
    
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
    
    # ===== 새로운 단계별 체인 생성 메소드들 =====
    
    def _create_plan_chain(self):
        """분석 전략 수립용 체인 생성"""
        from .prompt import PLAN_APPROACH_PROMPT
        prompt = ChatPromptTemplate.from_template(PLAN_APPROACH_PROMPT)
        return prompt | self.llm
    
    def _create_build_query_chain(self):
        """쿼리 구성용 체인 생성 (도구 포함)"""
        from .prompt import BUILD_QUERY_PROMPT
        prompt = ChatPromptTemplate.from_template(BUILD_QUERY_PROMPT)
        llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
        return prompt | llm_with_tools
    
    def _create_validate_chain(self):
        """결과 검증용 체인 생성"""
        from .prompt import VALIDATE_RESULTS_PROMPT
        prompt = ChatPromptTemplate.from_template(VALIDATE_RESULTS_PROMPT)
        return prompt | self.llm
    
    def _create_analyze_data_chain(self):
        """데이터 분석용 체인 생성"""
        from .prompt import ANALYZE_DATA_PROMPT
        prompt = ChatPromptTemplate.from_template(ANALYZE_DATA_PROMPT)
        return prompt | self.llm
    
    def _create_final_response_chain(self):
        """최종 응답 생성용 체인 생성"""
        from .prompt import GENERATE_FINAL_RESPONSE_PROMPT
        prompt = ChatPromptTemplate.from_template(GENERATE_FINAL_RESPONSE_PROMPT)
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
        """1단계: 질문 분석 (간소화) - 바로 쿼리 생성으로"""
        try:
            logger.info("🔍 질문 분석 시작 (간소화)")
            
            current_query = state["current_query"]
            
            # 새로운 질문이면 사용자 메시지 추가
            messages = state["messages"].copy()
            messages = self._clean_incomplete_tool_calls(messages)
            
            if current_query:
                user_msg = HumanMessage(
                    content=current_query,
                    additional_kwargs={"timestamp": datetime.now().isoformat()}
                )
                messages.append(user_msg)
                logger.info(f"💬 사용자 질문 추가: {current_query[:50]}...")
            
            # 바로 SQL 쿼리 생성 및 실행으로 진행
            response = await self.analysis_chain.ainvoke({"messages": messages}, config=config)
            messages.append(response)
            
            logger.info("✅ 질문 분석 완료 - 쿼리 실행으로 이동")
            
            return {
                **state,
                "messages": messages,
                "current_step": "execute_tools",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 질문 분석 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"질문 분석 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    async def plan_approach(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """2단계: 분석 전략 수립"""
        try:
            logger.info("📋 2단계: 분석 전략 수립 시작")
            
            requirements = state["requirements"]
            
            # 전략 수립 체인 호출
            plan_response = await self.plan_chain.ainvoke({
                "requirements": requirements
            })
            
            analysis_plan = plan_response.content
            logger.info("✅ 분석 전략 수립 완료")
            
            return {
                **state,
                "analysis_plan": analysis_plan,
                "current_step": "build_query",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 전략 수립 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"전략 수립 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    async def build_query(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """3단계: SQL 쿼리 구성"""
        try:
            logger.info("🔧 3단계: SQL 쿼리 구성 시작")
            
            requirements = state["requirements"]
            analysis_plan = state["analysis_plan"]
            
            # 쿼리 구성 체인 호출 (도구 포함)
            query_response = await self.build_query_chain.ainvoke({
                "requirements": requirements,
                "analysis_plan": analysis_plan
            })
            
            messages = state["messages"].copy()
            messages.append(query_response)
            
            logger.info("✅ SQL 쿼리 구성 완료")
            
            return {
                **state,
                "messages": messages,
                "current_step": "execute_query",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 쿼리 구성 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"쿼리 구성 중 오류가 발생했습니다: {str(e)}",
                "is_complete": True
            }
    
    async def validate_results(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """4단계: 결과 검증 및 품질 확인"""
        try:
            logger.info("✅ 4단계: 결과 검증 시작")
            
            validated_query = state.get("validated_query", "")
            sql_results = state.get("sql_results", [])
            
            if not sql_results:
                logger.warning("검증할 결과가 없습니다")
                return {
                    **state,
                    "result_quality_score": 0.0,
                    "current_step": "analyze_data"
                }
            
            # 결과 검증 체인 호출
            validate_response = await self.validate_chain.ainvoke({
                "validated_query": validated_query,
                "sql_results": "\n".join(sql_results)
            })
            
            # 품질 점수 추출 (간단한 파싱)
            content = validate_response.content
            quality_score = 85.0  # 기본값, 실제로는 응답에서 파싱
            
            logger.info(f"✅ 결과 검증 완료 - 품질 점수: {quality_score}")
            
            return {
                **state,
                "result_quality_score": quality_score,
                "current_step": "analyze_data",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 중 오류: {str(e)}")
            return {
                **state,
                "result_quality_score": 0.0,
                "current_step": "analyze_data"
            }
    
    async def analyze_data(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        """5단계: 데이터 분석 및 인사이트 도출"""
        try:
            logger.info("📊 5단계: 데이터 분석 시작")
            
            requirements = state["requirements"]
            sql_results = state.get("sql_results", [])
            quality_score = state.get("result_quality_score", 0.0)
            
            # 데이터 분석 체인 호출
            analysis_response = await self.analyze_data_chain.ainvoke({
                "requirements": requirements,
                "sql_results": "\n".join(sql_results),
                "result_quality_score": quality_score
            })
            
            data_insights = analysis_response.content
            logger.info("✅ 데이터 분석 완료")
            
            return {
                **state,
                "data_insights": data_insights,
                "current_step": "generate_response",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 데이터 분석 중 오류: {str(e)}")
            return {
                **state,
                "error_message": f"데이터 분석 중 오류가 발생했습니다: {str(e)}",
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
        """6단계: 최종 응답 생성"""
        try:
            logger.info("🎯 6단계: 최종 응답 생성 시작")
            
            current_query = state["current_query"]
            requirements = state.get("requirements", "")
            data_insights = state.get("data_insights", "")
            recommendations = state.get("recommendations", "")
            
            # 최종 응답 생성 체인 호출
            final_response = await self.final_response_chain.ainvoke({
                "current_query": current_query,
                "requirements": requirements,
                "data_insights": data_insights,
                "recommendations": recommendations
            })
            
            messages = state["messages"].copy()
            messages = self._clean_incomplete_tool_calls(messages)
            messages.append(final_response)
            
            logger.info("✅ 최종 응답 생성 완료")
            
            return {
                **state,
                "messages": messages,
                "is_complete": True,
                "current_step": "completed",
                "iteration_count": state["iteration_count"] + 1
            }
            
        except Exception as e:
            logger.error(f"❌ 최종 응답 생성 중 오류: {str(e)}")
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
        """고도화된 워크플로우 라우팅 조건 판단"""
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
        
        # 현재 단계 기반 라우팅
        current_step = state.get("current_step", "analyze_question")
        logger.info(f"📍 현재 단계: {current_step}")
        
        # 간소화된 단계별 라우팅
        if current_step == "analyze_question":
            # 도구 호출이 있는지 확인
            messages = state.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    logger.info("🔧 질문 분석 후 바로 도구 실행")
                    return "execute_tools"
            return "generate_response"
        elif current_step == "execute_tools":
            # 도구 실행 후 바로 응답 생성
            return "generate_response"
        elif current_step == "generate_response":
            return "end"
        
        # 도구 호출 상태 체크 (기존 로직 유지)
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            
            # 도구 호출이 있는 경우
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                logger.info(f"🔧 도구 호출 발견: {len(last_message.tool_calls)}개")
                return "execute_tools"
            
            # 도구 메시지 후에는 다음 단계로
            if isinstance(last_message, ToolMessage):
                if current_step == "build_query":
                    return "validate_results"
                else:
                    return "analyze_data"
        
        # 기본적으로 다음 단계로
        logger.info(f"📝 기본 라우팅: {current_step}")
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

# ===== 새로운 노드들의 래퍼 함수들 =====

async def plan_approach(state: Dict[str, Any]) -> Dict[str, Any]:
    """분석 전략 수립 노드 래퍼"""
    return await _sql_agent_node.plan_approach(state)

async def build_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """쿼리 구성 노드 래퍼"""
    return await _sql_agent_node.build_query(state)

async def validate_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """결과 검증 노드 래퍼"""
    return await _sql_agent_node.validate_results(state)

async def analyze_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """데이터 분석 노드 래퍼"""
    return await _sql_agent_node.analyze_data(state)

async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """최종 응답 생성 노드 래퍼"""
    return await _sql_agent_node.generate_response(state)

def should_continue(state: Dict[str, Any]) -> str:
    """라우팅 조건 판단 래퍼 (딕셔너리 기반)"""
    logger.info("🔄 should_continue 래퍼 호출")
    try:
        # 딕셔너리 상태를 AgentState 형식으로 변환 (고도화된 워크플로우용)
        agent_state: AgentState = {
            "messages": state.get("messages", []),
            "current_query": state.get("current_query", ""),
            
            # 분석 단계
            "requirements": state.get("requirements"),
            "analysis_plan": state.get("analysis_plan"),
            
            # 쿼리 단계
            "proposed_queries": state.get("proposed_queries", []),
            "validated_query": state.get("validated_query"),
            
            # 실행 및 결과 단계
            "sql_results": state.get("sql_results", []),
            "execution_errors": state.get("execution_errors", []),
            "result_quality_score": state.get("result_quality_score"),
            
            # 분석 단계
            "data_insights": state.get("data_insights"),
            "recommendations": state.get("recommendations"),
            
            # 제어 플래그
            "iteration_count": state.get("iteration_count", 0),
            "max_iterations": state.get("max_iterations", 10),
            "is_complete": state.get("is_complete", False),
            "error_message": state.get("error_message"),
            "used_tools": state.get("used_tools", []),
            "current_step": state.get("current_step", "analyze_question")
        }
        
        result = _sql_agent_node.should_continue_routing(agent_state)
        logger.info(f"✅ should_continue 래퍼 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ should_continue 래퍼 오류: {e}")
        return "end"
