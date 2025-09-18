"""
LLM Domain Models
LLM 요청/응답과 관련된 도메인 모델들
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMRequest:
    """LLM 요청 도메인 모델"""
    prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def validate(self) -> bool:
        """요청 유효성 검증"""
        if not self.prompt or len(self.prompt.strip()) == 0:
            return False
        if self.temperature < 0 or self.temperature > 2:
            return False
        if self.max_tokens and self.max_tokens <= 0:
            return False
        return True


@dataclass 
class LLMResponse:
    """LLM 응답 도메인 모델"""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_cost_estimate(self) -> float:
        """토큰 사용량 기반 비용 추정 (USD)"""
        # GPT-4o-mini 기준 대략적 계산
        input_cost = self.prompt_tokens * 0.00015 / 1000
        output_cost = self.completion_tokens * 0.0006 / 1000
        return input_cost + output_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """응답 요약 정보"""
        return {
            "content_length": len(self.content),
            "total_tokens": self.total_tokens,
            "response_time": self.response_time,
            "estimated_cost": self.get_cost_estimate(),
            "model": self.model
        }


@dataclass
class StreamChunk:
    """스트리밍 청크 도메인 모델"""
    content: str
    chunk_type: str = "content"  # content, tool_call, function_call, etc.
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_final(self) -> bool:
        """최종 청크인지 확인"""
        return self.chunk_type == "final" or self.content == ""
