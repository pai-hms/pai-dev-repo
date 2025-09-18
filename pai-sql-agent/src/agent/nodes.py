"""
LangGraph Agent 노드들
LLM 응답 생성을 중심으로 한 노드 구조

설계 원칙:
- 데이터와 로직의 일체화: 메시지 처리와 상태 관리를 함께 처리
- 선형원리: 직선적인 처리 흐름으로 가독성 향상
- SLAP: 각 함수는 동일한 추상화 수준 유지
"""
import logging
from typing import Dict, Any, TypedDict, List, Literal, Annotated, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, AnyMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages

from .prompt import get_database_schema, get_react_agent_initial_prompt, get_react_agent_response_prompt

logger = logging.getLogger(__name__)

# ===== 상태 정의 =====

class SupervisorInputState(TypedDict):
    """Supervisor의 Input"""
    query: str


class SupervisorOutputState(TypedDict):
    """Supervisor의 Output"""
    sql_query: str
    data: Dict[str, Dict[str, Any]]


class LangGraphAgentState(SupervisorInputState, SupervisorOutputState):
    """LangGraph Agent의 전체 상태 (input + output + hidden)"""
    messages: Annotated[List[BaseMessage], add_messages]


# 하위 호환성을 위한 별칭
ReactAgentState = LangGraphAgentState
AgentState = LangGraphAgentState


def create_initial_state(query: str, thread_id: str = "default") -> LangGraphAgentState:
    """초기 상태 생성"""
    return {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "sql_query": "",
        "data": {}
    }


# 하위 호환성
create_react_initial_state = create_initial_state


# ===== 메인 LLM 응답 생성 노드 =====

class LangAgentNode:
    """
    LLM을 통해 응답을 생성하는 메인 노드
    
    설계 원칙:
    - 데이터와 로직의 일체화: 메시지 처리, 토큰 관리, 도구 연동을 통합 관리
    - SLAP: 각 메서드는 동일한 추상화 수준 유지
    - Container을 통한 의존관계 명세: 필요한 서비스들을 DI로 주입
    """

    def __init__(
        self,
        execution_service: Any,
        tools: Dict[str, BaseTool],
        prompt_generator: Any,
        token_usage_service: Any,
    ):
        """
        Args:
            execution_service: 모델 실행 서비스
            tools: 사용 가능한 도구들 (이름 -> 도구 매핑)
            prompt_generator: 프롬프트 생성기
            token_usage_service: 토큰 사용량 서비스
        """
        self.execution_service = execution_service
        self.tools = tools
        self.prompt_generator = prompt_generator
        self.token_usage_service = token_usage_service

    async def __call__(
        self, state: LangGraphAgentState, config: RunnableConfig = None
    ) -> LangGraphAgentState:
        """
        메인 처리 함수 - LLM을 통한 응답 생성
        
        처리 흐름:
        1. 설정에서 챗봇 정보 추출
        2. 모델 로드 및 도구 바인딩
        3. 프롬프트 생성 및 체인 구성
        4. SQL 데이터 상태 관리
        5. LLM 호출 및 응답 생성
        6. 메타데이터 추가 (parent_id, timestamp)
        7. 토큰 사용량 누적
        """
        try:
            # 1. 챗봇 설정 추출
            chatbot_info = self._extract_chatbot_info(config)
            
            # 2. 모델 로드
            model = await self._load_chatmodel(chatbot_info, config)
            
            # 3. 프롬프트 생성
            prompt_template = await self._create_prompt_template(chatbot_info, config)
            chain = prompt_template | model
            
            # 4. 데이터 상태 관리
            state = self._manage_sql_data_state(state)
            
            # 5. LLM 호출
            message = await self._invoke_chain(chain, state["messages"], config)
            
            # 6. 메타데이터 추가
            message = self._add_message_metadata(message, state["messages"])
            state = self._add_metadata_to_existing_messages(state, message)
            
            # 7. 토큰 사용량 누적
            await self._accumulate_token_usage(chatbot_info, message)
            
            return {"messages": [message], "data": state.get("data", {})}
            
        except Exception as e:
            logger.error(f"❌ LangAgentNode 처리 오류: {e}")
            error_message = AIMessage(content=f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message], "data": state.get("data", {})}

    def _extract_chatbot_info(self, config: RunnableConfig) -> Dict[str, Any]:
        """설정에서 챗봇 정보 추출"""
        try:
            if config and "configurable" in config:
                chatbot_data = config["configurable"].get("chatbot", {})
                if isinstance(chatbot_data, dict):
                    return chatbot_data
            return {}
        except Exception:
            return {}

    async def _load_chatmodel(
        self, chatbot_info: Dict[str, Any], config: RunnableConfig
    ) -> BaseChatModel:
        """LLM 모델 로드 (스트리밍 지원)"""
        
        # LLM 서비스를 통해서만 모델 접근 (데이터 주권 원칙)
        from src.llm.service import get_llm_service
        
        llm_service = await get_llm_service()
        
        # 챗봇 정보에서 모델 설정 추출 (있는 경우)
        model_overrides = {
            "streaming": True  # 스트리밍 활성화
        }
        
        # 설정 오버라이드가 있으면 적용
        if model_overrides:
            config_obj = llm_service.update_config(**model_overrides)
            model = await llm_service.get_model(config_obj)
        else:
            # 기본 모델에 스트리밍 바인딩
            model = llm_service.llm.bind(streaming=True)
        
        # 사용할 도구 목록 가져오기
        tools = await self._get_tool_list(config)
        
        # 도구가 있으면 바인딩
        if tools:
            model = model.bind_tools(tools)
        
        return model

    async def _get_tool_list(self, config: RunnableConfig) -> List[BaseTool]:
        """설정에 따라 사용할 도구 목록 반환"""
        if not config or "configurable" not in config:
            return []
            
        configurable = config["configurable"]
        tools = []
        
        # 설정에 따라 도구 추가
        for tool_name, tool in self.tools.items():
            if configurable.get(tool_name, False):
                tools.append(tool)
        
        return tools

    async def _create_prompt_template(
        self, chatbot_info: Dict[str, Any], config: RunnableConfig
    ) -> Any:
        """프롬프트 템플릿 생성"""
        if self.prompt_generator:
            return await self.prompt_generator.create_prompt_template(chatbot_info, config)
        else:
            # 기본 프롬프트 사용
            from langchain_core.prompts import ChatPromptTemplate
            return ChatPromptTemplate.from_messages([
                ("system", "당신은 도움이 되는 AI 어시스턴트입니다."),
                ("human", "{messages}")
            ])

    def _manage_sql_data_state(self, state: LangGraphAgentState) -> LangGraphAgentState:
        """SQL 쿼리 결과 데이터 상태 관리"""
        if "data" not in state:
            state["data"] = {}

        # ToolMessage에서 SQL 결과 추출하여 저장
        for message in state["messages"]:
            if isinstance(message, ToolMessage) and message.name == "sql_query":
                if hasattr(message, 'artifact') and message.artifact:
                    if message.artifact.get("status") == "success":
                        data_id = message.artifact.get("data_id", str(datetime.now().timestamp()))
                        state["data"][data_id] = {
                            "sql_query": message.artifact.get("sql_query", ""),
                            "data": message.artifact.get("data", ""),
                            "timestamp": datetime.now().isoformat(),
                        }

        return state

    async def _invoke_chain(
        self, chain: Runnable, messages: List[AnyMessage], config: RunnableConfig
    ) -> AIMessage:
        """체인 호출"""
        try:
            return await chain.ainvoke({"messages": messages}, config=config)
        except Exception as e:
            logger.error(f"LLM 호출 중 에러: {e}")
            raise Exception(f"LLM 호출 중 에러: {e}")

    def _add_message_metadata(
        self, message: AIMessage, existing_messages: List[BaseMessage]
    ) -> AIMessage:
        """새 메시지에 메타데이터 추가"""
        # 가장 최근 human 메시지의 ID 찾기
        current_parent_id = None
        for msg in reversed(existing_messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_parent_id = getattr(msg, 'id', None)
                break

        # 메타데이터 추가
        if current_parent_id:
            if not hasattr(message, 'additional_kwargs') or message.additional_kwargs is None:
                message.additional_kwargs = {}
            
            message.additional_kwargs.update({
                "parent_id": current_parent_id,
                "timestamp": datetime.now().isoformat()
            })

        return message

    def _add_metadata_to_existing_messages(
        self, state: LangGraphAgentState, new_message: AIMessage
    ) -> LangGraphAgentState:
        """기존 메시지들에 메타데이터 추가"""
        current_parent_id = None
        if hasattr(new_message, 'additional_kwargs') and new_message.additional_kwargs:
            current_parent_id = new_message.additional_kwargs.get("parent_id")

        # 기존 메시지들에 메타데이터 추가
        for msg in state["messages"]:
            msg_type = getattr(msg, 'type', None)
            
            if msg_type == "human":
                # human 메시지에는 timestamp만 추가
                if not hasattr(msg, 'additional_kwargs') or msg.additional_kwargs is None:
                    msg.additional_kwargs = {}
                if "timestamp" not in msg.additional_kwargs:
                    msg.additional_kwargs["timestamp"] = datetime.now().isoformat()
            
            elif msg_type in ["ai", "tool"] and current_parent_id:
                # ai, tool 메시지에는 parent_id와 timestamp 추가
                if not hasattr(msg, 'additional_kwargs') or msg.additional_kwargs is None:
                    msg.additional_kwargs = {}
                
                if "parent_id" not in msg.additional_kwargs:
                    msg.additional_kwargs["parent_id"] = current_parent_id
                if "timestamp" not in msg.additional_kwargs:
                    msg.additional_kwargs["timestamp"] = datetime.now().isoformat()

        return state

    async def _accumulate_token_usage(self, chatbot_info: Dict[str, Any], message: AIMessage):
        """토큰 사용량 누적"""
        if not self.token_usage_service:
            return

        try:
            input_usage = 0
            output_usage = 0

            # 모델별 토큰 사용량 추출
            if hasattr(message, 'usage_metadata') and message.usage_metadata:
                input_usage = message.usage_metadata.get("input_tokens", 0)
                output_usage = message.usage_metadata.get("output_tokens", 0)
            elif hasattr(message, 'response_metadata') and message.response_metadata:
                input_usage = message.response_metadata.get("input_length", 0)
                output_usage = message.response_metadata.get("output_length", 0)

            # 토큰 사용량 기록 (실제 구현에서는 적절한 TokenUsage 객체 생성)
            if input_usage > 0 or output_usage > 0:
                logger.info(f"토큰 사용량 - Input: {input_usage}, Output: {output_usage}")
                
        except Exception as e:
            logger.error(f"토큰 사용량 누적 오류: {e}")


# ===== 하위 호환성을 위한 기존 노드들 =====

async def agent_node(state: ReactAgentState) -> ReactAgentState:
    """
    🧠 AGENT: LLM이 도구를 호출하거나 최종 응답을 생성
    """
    try:
        container = await DIContainer.get_instance()
        llm = container.get("llm")
        
        # SQL Agent용으로 도구를 바인딩한 LLM 사용
        llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)
        
        question = state["original_question"]
        iteration = state["iteration_count"]
        
        # DB 스키마 정보
        schema_info = get_database_schema()
        
        # 도구 실행 결과가 있는지 확인
        tool_results = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
        
        if not tool_results:
            # 첫 번째 반복: SQL 쿼리 생성 및 실행 지시
            prompt_text = get_react_agent_initial_prompt(
                question=question,
                schema_info=schema_info
            )
        else:
            # 도구 실행 결과가 있는 경우: 최종 응답 생성
            latest_tool_result = tool_results[-1].content
            prompt_text = get_react_agent_response_prompt(
                question=question,
                sql_result=latest_tool_result
            )
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        result = await llm_with_tools.ainvoke(prompt.format())
        
        # 도구 호출 여부 로깅
        if hasattr(result, 'tool_calls') and result.tool_calls:
            logger.info(f"🧠 도구 호출 발견: {len(result.tool_calls)}개")
        else:
            logger.info(f"🧠 텍스트 응답: {result.content[:100]}...")
        
        return {
            **state,
            "iteration_count": iteration + 1,
            "messages": state["messages"] + [result]
        }
        
    except Exception as e:
        logger.error(f"❌ 에이전트 노드 오류: {e}")
        error_response = f"죄송합니다. 질문 처리 중 오류가 발생했습니다: {str(e)}"
        return {
            **state,
            "final_response": error_response,
            "is_complete": True,
            "messages": state["messages"] + [AIMessage(content=error_response)]
        }


async def finalize_node(state: ReactAgentState) -> ReactAgentState:
    """
    📝 FINALIZE: 최종 응답 추출 및 완료 처리
    """
    try:
        # 마지막 AI 메시지를 최종 응답으로 사용
        ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
        
        if ai_messages:
            final_response = ai_messages[-1].content
        else:
            final_response = "응답을 생성할 수 없습니다."
        
        logger.info(f"📝 최종 응답 완료: {len(final_response)}자")
        
        return {
            **state,
            "final_response": final_response,
            "is_complete": True
        }
        
    except Exception as e:
        logger.error(f"❌ 최종화 노드 오류: {e}")
        return {
            **state,
            "final_response": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
            "is_complete": True
        }


# ===== 조건부 라우팅 함수 =====

def should_continue(state: ReactAgentState) -> Literal["tools", "finalize", "end"]:
    """
    다음 단계 결정: 도구 호출 → 완료 → 종료
    """
    
    # 완료 조건 확인
    if state["is_complete"]:
        return "end"
    
    # 최대 반복 횟수 초과
    if state["iteration_count"] >= state["max_iterations"]:
        logger.info("🔄 최대 반복 횟수 도달, 완료")
        return "finalize"
    
    # 마지막 메시지 확인
    last_message = state["messages"][-1] if state["messages"] else None
    
    if isinstance(last_message, AIMessage):
        # AI 메시지에 도구 호출이 있는지 확인
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info("🛠️ 도구 호출 감지됨 → tools")
            return "tools"
        else:
            # 도구 호출이 없으면 완료
            logger.info("📝 텍스트 응답 감지됨 → finalize")
            return "finalize"
    elif isinstance(last_message, ToolMessage):
        # 도구 실행 결과가 있으면 다시 에이전트로
        logger.info("👁️ 도구 결과 확인됨 → agent")
        return "agent"  # This should not happen in this routing function
    
    # 기본적으로 완료
    return "finalize"


# ===== 하위 호환성을 위한 기존 함수들 =====

# 기존 코드와의 호환성을 위해 유지
create_initial_state = create_react_initial_state

class AgentState(ReactAgentState):
    """하위 호환성을 위한 타입 별칭"""
    pass

# 기존 노드들을 새로운 구조로 매핑
reasoning_node = agent_node
action_node = agent_node  # ToolNode가 대신 처리
observation_node = agent_node  # 도구 실행 후 에이전트가 처리
generate_response_node = finalize_node

# 하위 호환성을 위한 라우팅 함수
def should_continue_react(state: ReactAgentState) -> Literal["reasoning", "action", "observation", "finalize", "end"]:
    """하위 호환성을 위한 라우팅 (실제로는 새로운 구조 사용)"""
    result = should_continue(state)
    
    # 새로운 구조를 기존 구조로 매핑
    if result == "tools":
        return "action"
    elif result == "finalize":
        return "finalize"
    elif result == "end":
        return "end"
    else:
        return "reasoning"