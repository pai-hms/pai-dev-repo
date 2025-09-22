"""
SQL Agent 노드들 - 간소화된 버전
"""
import logging
from typing import TypedDict, List, Annotated, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages

from src.agent.prompt import DATABASE_SCHEMA_INFO
from src.agent.utils import trim_messages_by_tokens, count_messages_tokens
from src.agent.settings import get_settings
from src.llm.service import get_llm_service
from src.agent.chain import create_sql_agent_chain, create_sql_response_chain

logger = logging.getLogger(__name__)


class SQLAgentState(TypedDict):
    """SQL Agent 상태"""
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    sql_query: str
    data: str


async def create_initial_state(query: str, thread_id: str = "default") -> SQLAgentState:
    """초기 상태 생성 - 세션 히스토리 포함"""
    messages = []
    
    try:
        # 단순히 현재 질문만 추가
        messages.append(HumanMessage(content=query))
        logger.info(f"PostgresSaver를 통한 멀티턴 대화 활성화 (thread_id: {thread_id})")
        
    except Exception as e:
        logger.warning(f"메시지 처리 실패: {e}")
        # Fallback: 기본 메시지만 사용
        messages = [HumanMessage(content=query)]
    
    return {
        "messages": messages,
        "query": query,
        "sql_query": "",
        "data": ""
    }


class SQLAgentNode:
    """SQL 에이전트 실행 노드 - Chain 기반"""
    
    def __init__(self, llm_service, tools):
        self.llm_service = llm_service
        self.tools = tools
        self._chain = None
    
    def _get_chain(self, model_name: str = "gpt-4o-mini"):
        """Chain을 지연 생성하여 반환"""
        if self._chain is None:
            logger.info("SQL Agent Chain 생성 중...")
            self._chain = create_sql_agent_chain(
                llm=self.llm_service.llm,
                tools=self.tools,
                model_name=model_name
            )
            logger.info("SQL Agent Chain 생성 완료")
        return self._chain
    
    async def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        try:
            logger.info("SQLAgentNode (Chain 기반) 실행 시작")
            logger.info(f"   사용 가능한 도구 수: {len(self.tools)}")
            logger.info(f"   도구 목록: {[tool.name for tool in self.tools]}")
            logger.info(f"   입력 메시지 수: {len(state.get('messages', []))}")
            
            # 현재 사용 중인 모델 확인
            current_model = "gpt-4o-mini"  # 기본값
            if config and hasattr(config, 'configurable') and config.configurable:
                current_model = config.configurable.get('model', current_model)
            
            logger.info(f"   사용 중인 모델: {current_model}")
            
            # 사용자 질문 추출 (로깅용)
            user_question = "질문 없음"
            if state.get('messages'):
                for msg in reversed(state['messages']):
                    if hasattr(msg, 'content') and msg.__class__.__name__ == 'HumanMessage':
                        user_question = msg.content
                        break
                logger.info(f"분석할 사용자 질문: '{user_question}'")
            
            # Chain 실행
            chain = self._get_chain(current_model)
            logger.info("Chain 실행 시작...")
            
            # Chain에 메시지 전달
            messages = state.get("messages", [])
            message = await chain.ainvoke(messages, config=config or {})
            
            logger.info(f"Chain 응답 수신: {type(message).__name__}")
            
            # 도구 호출 분석 (기존 로직 유지)
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info("=" * 60)
                logger.info(f"도구 호출 결정! 총 {len(message.tool_calls)}개 도구 호출")
                
                for i, tool_call in enumerate(message.tool_calls, 1):
                    tool_name = tool_call.get('name', 'Unknown')
                    tool_args = tool_call.get('args', {})
                    
                    logger.info(f"   도구 #{i}: {tool_name}")
                    if tool_name == 'sql_db_query' and 'query' in tool_args:
                        sql_query = tool_args['query']
                        logger.info(f"   생성된 SQL:")
                        logger.info(f"      {sql_query}")
                    elif tool_args:
                        logger.info(f"   인자: {tool_args}")
                logger.info("=" * 60)
            else:
                logger.info("일반 텍스트 응답 (도구 호출 없음)")
                if hasattr(message, 'content') and message.content:
                    logger.info(f"   응답 내용: {message.content[:100]}...")
            
            return {"messages": [message]}
            
        except Exception as e:
            logger.error(f"SQL Agent 노드 (Chain) 오류: {e}", exc_info=True)
            error_message = AIMessage(content=f"처리 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message]}


class SQLResponseNode:
    """최종 응답 생성 노드 - Chain 기반"""
    
    def __init__(self):
        self._chain = None
    
    async def _get_chain(self):
        """Response Chain을 비동기로 생성하여 반환"""
        if self._chain is None:
            logger.info("SQL Response Chain 생성 중...")
            llm_service = await get_llm_service()
            self._chain = create_sql_response_chain(llm=llm_service.llm)
            logger.info("SQL Response Chain 생성 완료")
        return self._chain
    
    async def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        """SQL 결과를 바탕으로 사용자 친화적 응답 생성 - Chain 사용"""
        try:
            logger.info("SQLResponseNode (Chain 기반) 실행 시작")
            
            # 현재 상태에서 정보 추출
            query = state.get("query", "")
            sql_query = state.get("sql_query", "")
            data = state.get("data", "")
            
            logger.info(f"응답 생성 컨텍스트: query={len(query)}자, sql={len(sql_query)}자, data={len(data)}자")
            
            # Chain 가져오기 및 실행
            chain = await self._get_chain()
            logger.info("Response Chain 실행 시작...")
            
            # Chain에 컨텍스트 데이터 전달
            context_data = {
                "query": query,
                "sql_query": sql_query,
                "data": data
            }
            
            response = await chain.ainvoke(context_data, config=config or {})
            
            logger.info(f"Response Chain 응답 생성 완료: {len(response.content)} 글자")
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"응답 생성 (Chain) 오류: {e}", exc_info=True)
            error_response = AIMessage(content=f"응답 생성 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_response]}

