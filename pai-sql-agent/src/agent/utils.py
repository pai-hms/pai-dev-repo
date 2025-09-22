"""
Agent 유틸리티 함수들
Context Length 관리 및 토큰 계산 기능
"""
import json
import logging
from typing import List, Dict, Any, Optional, Callable, Union
from functools import lru_cache
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage

try:
    import tiktoken
except ImportError:
    tiktoken = None

logger = logging.getLogger(__name__)


class TokenCounter:
    """모델별 토큰 계산 클래스"""
    
    def __init__(self):
        self._token_count_cache: Dict[str, Callable[[str], int]] = {}
    
    @lru_cache(maxsize=128)
    def get_token_counter(self, model_name: str) -> Callable[[str], int]:
        """모델별 토큰 계산 함수 반환 (캐시됨)"""
        if model_name in self._token_count_cache:
            return self._token_count_cache[model_name]
        
        if model_name.startswith("gpt-") and tiktoken is not None:
            # OpenAI GPT 모델
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                counter = lambda x: len(encoding.encode(x))
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding: {e}")
                counter = self._approximate_token_count
        elif model_name.startswith("gemini-"):
            # Google Gemini 모델 (근사치 계산)
            counter = self._approximate_token_count
        else:
            # 기본 근사치 계산
            logger.warning(f"Unknown model {model_name}, using approximate token count")
            counter = self._approximate_token_count
        
        self._token_count_cache[model_name] = counter
        return counter
    
    def _approximate_token_count(self, text: str) -> int:
        """근사 토큰 계산 (1 토큰 ≈ 4 문자)"""
        if not text:
            return 0
        # 한글/영문 혼합 고려: 평균 3.5 문자 = 1 토큰
        return max(1, len(text) // 4)
    
    def count_message_tokens(self, message: BaseMessage, model_name: str) -> int:
        """메시지의 토큰 수 계산"""
        counter = self.get_token_counter(model_name)
        
        # 메시지 내용
        content_tokens = counter(str(message.content)) if message.content else 0
        
        # 메시지 타입별 추가 토큰 (메타데이터)
        if isinstance(message, SystemMessage):
            overhead = 10  # 시스템 메시지 오버헤드
        elif isinstance(message, HumanMessage):
            overhead = 5   # 사용자 메시지 오버헤드
        elif isinstance(message, AIMessage):
            overhead = 8   # AI 메시지 오버헤드
            # 도구 호출이 있는 경우 추가 토큰
            if hasattr(message, 'tool_calls') and message.tool_calls:
                overhead += len(message.tool_calls) * 20
        elif isinstance(message, ToolMessage):
            overhead = 15  # 도구 메시지 오버헤드
        else:
            overhead = 5   # 기본 오버헤드
        
        return content_tokens + overhead
    
    def count_messages_tokens(self, messages: List[BaseMessage], model_name: str) -> int:
        """메시지 리스트의 총 토큰 수 계산"""
        if not messages:
            return 0
        
        total_tokens = 0
        for message in messages:
            total_tokens += self.count_message_tokens(message, model_name)
        
        # 대화 컨텍스트 오버헤드 (메시지 간 구분자 등)
        context_overhead = len(messages) * 2
        
        return total_tokens + context_overhead
    
    def estimate_context_tokens(self, context: Union[Dict[str, Any], str], model_name: str) -> int:
        """컨텍스트 데이터의 토큰 수 추정"""
        counter = self.get_token_counter(model_name)
        
        if isinstance(context, str):
            return counter(context)
        elif isinstance(context, dict):
            # JSON 직렬화 후 토큰 계산
            json_str = json.dumps(context, ensure_ascii=False, separators=(',', ':'))
            return counter(json_str)
        else:
            # 문자열로 변환 후 계산
            return counter(str(context))


# 전역 토큰 카운터 인스턴스
_token_counter = TokenCounter()


# count_tokens_approximately와 count_message_tokens 제거됨
# 직접 호출되지 않고 내부적으로만 사용되거나 완전 미사용


def count_messages_tokens(messages: List[BaseMessage], model_name: str = "gpt-4o-mini") -> int:
    """메시지 리스트 토큰 수 계산"""
    return _token_counter.count_messages_tokens(messages, model_name)


def estimate_context_tokens(context: Union[Dict[str, Any], str], model_name: str = "gpt-4o-mini") -> int:
    """컨텍스트 토큰 수 추정"""
    return _token_counter.estimate_context_tokens(context, model_name)


def trim_messages_by_tokens(
    messages: List[BaseMessage],
    max_tokens: int,
    model_name: str = "gpt-4o-mini",
    strategy: str = "last",
    preserve_system: bool = True
) -> List[BaseMessage]:
    """
    토큰 수 기준으로 메시지 트리밍
    
    Args:
        messages: 메시지 리스트
        max_tokens: 최대 토큰 수
        model_name: 모델 이름
        strategy: 트리밍 전략 ("last": 최신 우선, "first": 오래된 것 우선)
        preserve_system: 시스템 메시지 보존 여부
    
    Returns:
        트리밍된 메시지 리스트
    """
    if not messages:
        return []
    
    # 시스템 메시지 분리
    system_messages = []
    other_messages = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage) and preserve_system:
            system_messages.append(msg)
        else:
            other_messages.append(msg)
    
    # 시스템 메시지 토큰 계산
    system_tokens = count_messages_tokens(system_messages, model_name)
    available_tokens = max_tokens - system_tokens
    
    if available_tokens <= 0:
        logger.warning(f"System messages exceed max_tokens ({system_tokens} > {max_tokens})")
        return system_messages[:1] if system_messages else []
    
    # 다른 메시지들 트리밍
    trimmed_messages = []
    current_tokens = 0
    
    if strategy == "last":
        # 최신 메시지부터 역순으로 추가
        for msg in reversed(other_messages):
            msg_tokens = _token_counter.count_message_tokens(msg, model_name)
            if current_tokens + msg_tokens <= available_tokens:
                trimmed_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
    else:  # strategy == "first"
        # 오래된 메시지부터 순서대로 추가
        for msg in other_messages:
            msg_tokens = _token_counter.count_message_tokens(msg, model_name)
            if current_tokens + msg_tokens <= available_tokens:
                trimmed_messages.append(msg)
                current_tokens += msg_tokens
            else:
                break
    
    # 시스템 메시지 + 트리밍된 메시지 결합
    result = system_messages + trimmed_messages
    
    final_tokens = count_messages_tokens(result, model_name)
    logger.info(f"Message trimming: {len(messages)} → {len(result)} messages, "
                f"tokens: {count_messages_tokens(messages, model_name)} → {final_tokens}")
    
    return result


def should_filter_context(context: Union[Dict[str, Any], str], max_tokens: int, model_name: str) -> bool:
    """컨텍스트 필터링 필요 여부 판단"""
    current_tokens = estimate_context_tokens(context, model_name)
    return current_tokens > max_tokens
