"""
SQL Agent 노드들
SQL 에이전트의 각 단계를 담당하는 노드 클래스들
"""
import logging
from typing import Annotated, TypedDict, List, Tuple
from datetime import datetime
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage, AnyMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable, RunnableConfig

from .external_database.database import CustomSQLDatabase
from .prompt import QUERY_GENERATION_PROMPT

logger = logging.getLogger(__name__)


# ===== 상태 정의 =====

class SQLAgentInputState(TypedDict):
    """SQL Agent의 Input"""
    query: str


class SQLAgentOutputState(TypedDict):
    """SQL Agent의 Output"""
    sql_query: str
    data: str


class SQLAgentOverallState(SQLAgentInputState, SQLAgentOutputState):
    """SQL Agent의 전체 상태 (input + output + hidden)"""
    messages: Annotated[list, add_messages]


# ===== 노드 클래스들 =====

class QueryGenerationPromptNode:
    """Query 생성 프롬프트를 준비하는 노드"""

    def __call__(self, state: SQLAgentInputState, config: RunnableConfig = None) -> SQLAgentOverallState:
        """DB 스키마 정보를 포함한 SQL 쿼리 생성용 프롬프트 준비"""
        
        try:
            # 데이터베이스 연결 정보 설정에서 가져오기
            db_url = config["configurable"]["sql_agent"]["db_url"]
            db = CustomSQLDatabase.from_uri(db_url)
            
            query = state["query"]
            
            # 시스템 메시지 생성
            messages = [
                SystemMessage(
                    QUERY_GENERATION_PROMPT.format(
                        dialect=config["configurable"].get("dialect", "postgresql"),
                        table_infos=db.get_table_info(),
                    )
                ),
                HumanMessage(query),
            ]
            
            return {"messages": messages}
            
        except Exception as e:
            logger.error(f"프롬프트 생성 실패: {e}")
            # 오류 발생 시 기본 메시지 반환
            return {
                "messages": [
                    SystemMessage("SQL 쿼리 생성을 위한 스키마 정보를 가져올 수 없습니다."),
                    HumanMessage(state["query"])
                ]
            }


class QueryGenerationAgentNode:
    """Query 생성 에이전트 - LLM을 사용해 SQL 쿼리 생성"""

    def __init__(
        self,
        execution_service: ModelExecutionService,
        token_usage_service: TokenUsageService,
        tools: List[BaseTool],
    ):
        self.execution_service = execution_service
        self.tools = tools
        self.token_usage_service = token_usage_service

    async def __call__(self, state: SQLAgentOverallState, config: RunnableConfig = None) -> SQLAgentOverallState:
        """LLM을 사용해 SQL 쿼리를 생성하고 Tool Call 실행"""
        
        try:
            # chatbot = Chatbot.from_dict(config["configurable"]["chatbot"])  # 제거됨
            model = await self.load_chatmodel(chatbot)

            # 가장 최근 human 메시지의 id를 찾기 (메타데이터용)
            current_parent_id = None
            for message in reversed(state["messages"]):
                if hasattr(message, 'type') and message.type == "human":
                    current_parent_id = getattr(message, 'id', None)
                    break

            # LLM 호출
            message = await self.invoke_chain(model, state["messages"], config)

            # 생성된 AI 메시지에 parent_id 추가
            if current_parent_id:
                message_type = getattr(message, 'type', None)
                if message_type in ["ai", "tool"]:
                    if hasattr(message, 'additional_kwargs'):
                        if message.additional_kwargs is None:
                            message.additional_kwargs = {}
                        message.additional_kwargs["parent_id"] = current_parent_id
                        message.additional_kwargs["timestamp"] = datetime.now().isoformat()
                    else:
                        message.additional_kwargs = {
                            "parent_id": current_parent_id,
                            "timestamp": datetime.now().isoformat()
                        }

            # 토큰 사용량 누적
            await self.accumulate_token_usage(chatbot, message)
            
            return {"messages": [message]}
            
        except Exception as e:
            logger.error(f"SQL 쿼리 생성 실패: {e}")
            return {
                "messages": [
                    AIMessage(content=f"SQL 쿼리 생성 중 오류가 발생했습니다: {str(e)}")
                ]
            }
    
    async def load_chatmodel(self, chatbot: Chatbot) -> BaseChatModel:
        """Chatbot의 모델 설정을 기반으로 언어 모델 로드"""
        model = await self.execution_service.load_llm_model(chatbot.model_id)
        
        # 모델이 tool calling 기능을 지원하는지 확인
        model_config = getattr(model, 'model_config', {})
        enable_tool_calling = model_config.get("enable_tool_calling", True)
        
        if enable_tool_calling and self.tools:
            try:
                return model.bind_tools(self.tools)
            except Exception as e:
                logger.error(f"도구 바인딩 실패: {e}")
        
        return model
    
    async def invoke_chain(self, chain: Runnable, messages: List[AnyMessage], config: RunnableConfig):
        """Chain을 실행"""
        try:
            return await chain.ainvoke(messages, config=config)
        except Exception as e:
            logger.error(f"LLM 호출 중 오류: {e}")
            raise RagStackException(f"LLM 호출 중 오류: {e}")


class QuerySummaryNode:
    """Query 결과를 요약하는 노드"""

    def __call__(self, state: SQLAgentOverallState, config: RunnableConfig = None) -> SQLAgentOutputState:
        """ToolMessage에서 최종 실행된 SQL 쿼리와 결과 데이터를 추출"""
        
        try:
            # 최근 Tool Call에서 SQL 쿼리 추출
            query, tool_call_id = self._get_last_tool_call_id(state["messages"])
            
            # Tool Call ID를 사용해 결과 데이터 추출
            data = self._get_data_from_tool_call_id(state["messages"], tool_call_id)
            
            return {
                "sql_query": query,
                "data": data,
            }
            
        except Exception as e:
            logger.error(f"쿼리 요약 실패: {e}")
            return {
                "sql_query": "오류: SQL 쿼리를 추출할 수 없습니다.",
                "data": f"오류: {str(e)}"
            }

    def _get_last_tool_call_id(self, messages: List[AnyMessage]) -> Tuple[str, str]:
        """최근 Tool Call ID를 반환"""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    # SQL 실행 도구 찾기
                    if tool_call["name"] in ["sql_db_query", "sql_query"]:
                        query = tool_call["args"]["query"]
                        tool_call_id = tool_call["id"]
                        return query, tool_call_id
        
        return "쿼리를 찾을 수 없습니다.", None
    
    def _get_data_from_tool_call_id(self, messages: List[AnyMessage], tool_call_id: str) -> str:
        """Tool Call ID를 사용해 데이터를 반환"""
        if tool_call_id is None:
            return "Tool Call ID를 찾을 수 없습니다."
        
        for message in reversed(messages):
            if isinstance(message, ToolMessage) and message.tool_call_id == tool_call_id:
                return message.content
        
        return "결과 데이터를 찾을 수 없습니다."
