"""
SQL Agent Chain 구현
LangGraph와 함께 사용할 수 있는 Chain 구조
"""
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import BaseTool

from src.agent.prompt import DATABASE_SCHEMA_INFO
from src.agent.utils import trim_messages_by_tokens, count_messages_tokens
from src.agent.settings import get_settings

logger = logging.getLogger(__name__)


def create_sql_agent_chain(
    llm: BaseChatModel,
    tools: List[BaseTool],
    prompt: Optional[str] = None,
    prompt_variables: Optional[Dict[str, Any]] = None,
    model_name: str = "gpt-4o-mini"
):
    """SQL Agent 체인을 생성하는 함수
    
    Args:
        llm: 언어 모델
        tools: 사용할 도구 리스트
        prompt: 사용자 정의 프롬프트 (선택사항)
        prompt_variables: 프롬프트 변수 (선택사항)
        model_name: 모델명 (토큰 계산용)
    
    Returns:
        실행 가능한 Chain
    """
    
    # 기본 프롬프트 설정
    if not prompt:
        prompt = f"""당신은 데이터 전문 SQL 분석가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

**응답 가이드라인:**
1. 데이터 관련 질문: SQL 쿼리를 생성하고 sql_db_query 도구로 실행
2. 인사말/간단한 질문: 친근하게 응답하고 도움이 필요한 경우 제안
3. 모든 응답은 한국어로 작성

이전 대화 맥락을 고려하여 연속적인 대화를 지원해주세요."""

    # 프롬프트 변수가 있는 경우 템플릿 적용
    if prompt_variables:
        prompt = prompt.format(**prompt_variables)

    # 시스템 프롬프트 템플릿 생성
    system_prompt = ChatPromptTemplate.from_messages([
        ("system", prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # LLM에 도구 바인딩
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    
    # 도구 매핑 생성
    toolkits = {tool.name: tool for tool in tools}

    def format_inputs(messages: List[BaseMessage]) -> Dict[str, Any]:
        """LLM에 전달할 메시지를 포맷팅하는 함수"""
        logger.info(f"Chain 입력 메시지 수: {len(messages)}")
        
        # Context Length 관리
        settings = get_settings()
        processed_messages = messages.copy()
        
        if processed_messages:
            # 현재 토큰 수 계산
            current_tokens = count_messages_tokens(processed_messages, model_name)
            logger.info(f"Chain 현재 토큰 수: {current_tokens}")
            
            # 토큰 수가 제한을 초과하는 경우 트리밍
            if current_tokens > settings.TRIM_MAX_TOKENS:
                logger.info(f"Chain 토큰 수 초과 ({current_tokens} > {settings.TRIM_MAX_TOKENS}), 메시지 트리밍")
                processed_messages = trim_messages_by_tokens(
                    messages=processed_messages,
                    max_tokens=settings.TRIM_MAX_TOKENS,
                    model_name=model_name,
                    strategy="last",
                    preserve_system=True
                )
                logger.info(f"Chain 메시지 트리밍 완료: {len(messages)} → {len(processed_messages)}")
        
        # 도구 메시지 특별 처리
        outputs = []
        for message in processed_messages:
            if not isinstance(message, ToolMessage):
                outputs.append(message)
                continue
            
            tool_name = message.name
            # 기본적으로 도구 메시지는 그대로 전달
            # 필요시 특별한 포맷팅 로직 추가 가능
            outputs.append(message)
        
        logger.info(f"Chain 최종 메시지 수: {len(outputs)}")
        return {"messages": outputs}

    # Chain 구성: 입력 포맷팅 → 시스템 프롬프트 → LLM
    chain = RunnableLambda(format_inputs) | system_prompt | llm_with_tools
    
    logger.info(f"SQL Agent Chain 생성 완료 (도구 수: {len(tools)})")
    return chain

