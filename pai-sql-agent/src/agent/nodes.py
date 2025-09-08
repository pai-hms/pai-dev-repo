"""에이전트 노드 정의."""

import logging
from datetime import datetime
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages

from src.agent.prompt import PromptGenerator
from src.config import settings

logger = logging.getLogger(__name__)


class AgentInputState(TypedDict):
    """에이전트 입력 상태."""
    query: str


class AgentOutputState(TypedDict):
    """에이전트 출력 상태."""
    sql_query: str
    data: Dict[str, Dict[str, Any]]


class LangGraphAgentState(AgentInputState, AgentOutputState):
    """에이전트 전체 상태 (입력 + 출력 + 숨김)."""
    messages: Annotated[list, add_messages]


class LangAgentNode:
    """LLM을 통해 응답을 생성하는 노드."""

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Dict[str, BaseTool],
        prompt_generator: PromptGenerator,
    ):
        self.llm = llm
        self.tools = tools
        self.prompt_generator = prompt_generator

    async def __call__(
        self, state: LangGraphAgentState, config: RunnableConfig = None
    ) -> LangGraphAgentState:
        """노드 실행."""
        model = await self.load_chatmodel(config)
        prompt_template = await self.prompt_generator.create_prompt_template(config)
        chain = prompt_template | model

        # 데이터 상태 확인 및 관리
        if "data" not in state:
            state["data"] = {}

        # SQL 쿼리 결과 저장
        for m in state["messages"]:
            if isinstance(m, ToolMessage) and m.name == "execute_sql_query":
                if hasattr(m, 'artifact') and m.artifact:
                    data_id = m.artifact.get("data_id")
                    if data_id:
                        state["data"][data_id] = {
                            "sql_query": m.artifact.get("sql_query", ""),
                            "data": m.artifact.get("data", {}),
                            "timestamp": datetime.now().isoformat(),
                        }

        # 가장 최근 human 메시지의 id 찾기
        current_parent_id = None
        for message in reversed(state["messages"]):
            if hasattr(message, 'type') and message.type == "human":
                current_parent_id = getattr(message, 'id', None)
                break

        message = await self.invoke_chain(chain, state["messages"], config)

        # 새로 생성된 AI 메시지에 메타데이터 추가
        if current_parent_id:
            self._add_message_metadata(message, current_parent_id)

        # 기존 메시지들에 메타데이터 추가
        self._update_existing_messages_metadata(state["messages"], current_parent_id)

        return {"messages": [message], "data": state["data"]}

    async def load_chatmodel(self, config: RunnableConfig) -> BaseChatModel:
        """설정에 맞는 모델을 로드."""
        tools = await self.get_tool_list(config)
        
        # 도구 바인딩 시도
        try:
            return self.llm.bind_tools(tools)
        except Exception as e:
            logger.error(f"도구 바인딩 오류: {e}")
            return self.llm

    async def get_tool_list(self, config: RunnableConfig) -> List[BaseTool]:
        """도구 목록 반환."""
        configurable = config.get("configurable", {})
        use_sql_agent = configurable.get("sql_agent", False)

        tools = []
        if use_sql_agent and "sql_agent" in self.tools:
            tools.append(self.tools["sql_agent"])

        return tools

    async def invoke_chain(
        self, chain: Runnable, messages: List[AnyMessage], config: RunnableConfig
    ):
        """체인 호출."""
        try:
            return await chain.ainvoke({"messages": messages}, config=config)
        except Exception as e:
            logger.error(f"LLM 호출 중 오류 발생: {e}")
            raise Exception(f"LLM 호출 중 오류 발생: {e}")

    def _add_message_metadata(self, message: AIMessage, parent_id: str):
        """메시지에 메타데이터 추가."""
        if hasattr(message, 'additional_kwargs'):
            if message.additional_kwargs is None:
                message.additional_kwargs = {}
            message.additional_kwargs.update({
                "parent_id": parent_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            message.additional_kwargs = {
                "parent_id": parent_id,
                "timestamp": datetime.now().isoformat()
            }

    def _update_existing_messages_metadata(self, messages: List[AnyMessage], parent_id: str):
        """기존 메시지들에 메타데이터 업데이트."""
        for msg in messages:
            msg_type = getattr(msg, 'type', None)
            
            if msg_type == "human":
                # human 메시지에는 timestamp만 추가
                if not hasattr(msg, 'additional_kwargs') or msg.additional_kwargs is None:
                    msg.additional_kwargs = {"timestamp": datetime.now().isoformat()}
                elif "timestamp" not in msg.additional_kwargs:
                    msg.additional_kwargs["timestamp"] = datetime.now().isoformat()
            
            elif msg_type in ["ai", "tool"] and parent_id:
                # ai, tool 메시지에는 parent_id와 timestamp 추가
                if not hasattr(msg, 'additional_kwargs') or msg.additional_kwargs is None:
                    msg.additional_kwargs = {
                        "parent_id": parent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    if "parent_id" not in msg.additional_kwargs:
                        msg.additional_kwargs["parent_id"] = parent_id
                    if "timestamp" not in msg.additional_kwargs:
                        msg.additional_kwargs["timestamp"] = datetime.now().isoformat()
