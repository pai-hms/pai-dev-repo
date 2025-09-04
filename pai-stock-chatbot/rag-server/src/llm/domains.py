# rag-server/src/llm/domains.py
from dataclasses import dataclass
from typing import List, Literal, Optional

# 간소화된 타입 정의 (주식 챗봇 특화)
CompletionVendorName = Literal["OpenAI", "Custom"]
CompletionModelName = Literal[
    "gpt-3.5-turbo",
    "gpt-4o-mini", 
    "gpt-4o",
    "custom-llm"
]

@dataclass
class LLMCompletionModel:
    """LLM 완료 모델 정보"""
    model_name: CompletionModelName
    model_url: str
    tool_calling: bool
    temperature: float = 0.1
    max_tokens: Optional[int] = None

@dataclass
class CompletionVendor:
    """LLM 벤더 정보"""
    vendor_name: CompletionVendorName
    model_list: List[LLMCompletionModel]
    api_key_required: bool = True

@dataclass
class LLMConfig:
    """LLM 설정 정보"""
    default_model: CompletionModelName
    system_prompt: str
    vendors: List[CompletionVendor]