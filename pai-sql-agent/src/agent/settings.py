"""
Agent 설정
에이전트 관련 설정 관리 (프롬프트는 prompt.py로 분리됨)
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.config.settings import get_settings


@dataclass
class AgentConfig:
    """에이전트 설정"""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4000
    max_iterations: int = 10
    
    # 스트리밍 설정
    enable_streaming: bool = True
    stream_mode: str = "messages"  # "messages" or "values"
    
    # 검증 설정
    enable_query_validation: bool = True
    max_query_length: int = 10000


def get_agent_config() -> AgentConfig:
    """에이전트 설정 반환"""
    return AgentConfig()


# 프롬프트는 prompt.py 파일에서 import
from .prompt import SYSTEM_PROMPT, HUMAN_PROMPT, TABLE_SCHEMA_INFO