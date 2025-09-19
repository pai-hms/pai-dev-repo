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
from src.llm.service import get_llm_service
from src.session.service import get_session_service

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
        # ✅ PostgresSaver가 멀티턴 대화를 처리하므로 Session Service는 비활성화
        # 단순히 현재 질문만 추가
        messages.append(HumanMessage(content=query))
        logger.info(f"📚 PostgresSaver를 통한 멀티턴 대화 활성화 (thread_id: {thread_id})")
        
    except Exception as e:
        logger.warning(f"⚠️ 메시지 처리 실패: {e}")
        # Fallback: 기본 메시지만 사용
        messages = [HumanMessage(content=query)]
    
    return {
        "messages": messages,
        "query": query,
        "sql_query": "",
        "data": ""
    }




class SQLPromptNode:
    """SQL 프롬프트 생성 노드"""
    
    def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        logger.info("📝 SQLPromptNode 실행 시작")
        logger.info(f"   입력 쿼리: '{state.get('query', '')}'")
        logger.info(f"   기존 메시지 수: {len(state.get('messages', []))}")
        
        # ✅ 시스템 프롬프트를 맨 앞에 추가
        system_prompt = f"""당신은 데이터 전문 SQL 분석가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

**응답 가이드라인:**
1. 데이터 관련 질문: SQL 쿼리를 생성하고 sql_db_query 도구로 실행
2. 인사말/간단한 질문: 친근하게 응답하고 도움이 필요한 경우 제안
3. 모든 응답은 한국어로 작성

이전 대화 맥락을 고려하여 연속적인 대화를 지원해주세요."""

        # 기존 메시지에 시스템 프롬프트만 앞에 추가
        messages = [SystemMessage(content=system_prompt)] + state.get("messages", [])
        
        logger.info(f"   최종 메시지 구성: System + {len(state.get('messages', []))}개 히스토리")
        
        return {"messages": messages}


class SQLAgentNode:
    """SQL 에이전트 실행 노드"""
    
    def __init__(self, llm_service, tools):
        self.llm_service = llm_service
        self.tools = tools
    
    async def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        try:
            logger.info("🤖 SQLAgentNode 실행 시작")
            logger.info(f"   사용 가능한 도구 수: {len(self.tools)}")
            logger.info(f"   도구 목록: {[tool.name for tool in self.tools]}")
            logger.info(f"   입력 메시지 수: {len(state.get('messages', []))}")
            
            # ✅ 사용자 질문 추출 (시스템 메시지 제외)
            user_question = "질문 없음"
            if state.get('messages'):
                # 마지막 Human 메시지 찾기
                for msg in reversed(state['messages']):
                    if hasattr(msg, 'content') and msg.__class__.__name__ == 'HumanMessage':
                        user_question = msg.content
                        break
                logger.info(f"👤 분석할 사용자 질문: '{user_question}'")
            
            llm_with_tools = self.llm_service.llm.bind_tools(self.tools)
            logger.info("🔧 LLM에 도구 바인딩 완료")
            
            logger.info("🧠 LLM 추론 시작 - 질문 분석 및 도구 선택...")
            message = await llm_with_tools.ainvoke(state["messages"])
            logger.info(f"✅ LLM 응답 수신: {type(message).__name__}")
            
            # 도구 호출 분석
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info("=" * 60)
                logger.info(f"🎯 도구 호출 결정! 총 {len(message.tool_calls)}개 도구 호출")
                
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
                logger.info("📝 일반 텍스트 응답 (도구 호출 없음)")
                if hasattr(message, 'content') and message.content:
                    logger.info(f"   응답 내용: {message.content[:100]}...")
            
            return {"messages": [message]}
            
        except Exception as e:
            logger.error(f"❌ SQL Agent 노드 오류: {e}", exc_info=True)
            error_message = AIMessage(content=f"처리 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message]}

class SQLSummaryNode:
    """SQL 결과 요약 노드"""
    
    def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        # 마지막 도구 호출 결과에서 SQL과 데이터 추출
        sql_query = ""
        data = ""
        
        for message in reversed(state["messages"]):
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call["name"] == "sql_db_query":
                        sql_query = tool_call["args"]["query"]
                        break
            elif hasattr(message, 'type') and message.type == "tool":
                data = message.content
                break
        
        return {
            "sql_query": sql_query,
            "data": data
        }


class SQLResponseNode:
    """최종 응답 생성 노드"""
    
    def __init__(self):
        pass
    
    async def __call__(self, state: SQLAgentState, config: RunnableConfig = None) -> SQLAgentState:
        """SQL 결과를 바탕으로 사용자 친화적 응답 생성"""
        try:
            llm_service = await get_llm_service()
            
            # 현재 상태에서 정보 추출
            query = state.get("query", "")
            sql_query = state.get("sql_query", "")
            data = state.get("data", "")
        
            
            # LLM을 사용해 최종 응답 생성
            response_prompt = f"""다음 정보를 바탕으로 사용자에게 친화적이고 이해하기 쉬운 답변을 생성해주세요.

사용자 질문: {query}

실행된 SQL: {sql_query}

쿼리 결과:
{data}

요구사항:
1. 구체적인 숫자와 함께 명확한 답변 제공
2. 필요시 추가 해석이나 인사이트 포함
3. 한국어로 자연스럽게 작성
4. 테이블 형태 데이터는 요약해서 설명

답변:"""

            messages = [
                SystemMessage(content="당신은 데이터 분석 결과를 사용자에게 친화적으로 설명하는 전문가입니다."),
                HumanMessage(content=response_prompt)
            ]
            
            response = await llm_service.llm.ainvoke(messages)
            
            # ✅ PostgresSaver가 자동으로 상태를 저장하므로 수동 저장 불필요
            logger.info(f"최종 응답 생성 완료: {len(response.content)} 글자")
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"응답 생성 오류: {e}")
            error_response = AIMessage(content=f"응답 생성 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_response]}

