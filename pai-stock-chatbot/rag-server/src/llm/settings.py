# rag-server/src/llm/settings.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class LLMSettings(BaseSettings):
    """LLM 관련 설정"""
    
    # OpenAI 설정
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.1
    
    # 시스템 프롬프트
    SYSTEM_PROMPT: str = """당신은 주식 정보와 계산을 도와주는 AI 어시스턴트입니다."""

    class Config:
        # 프로젝트 루트의 .env 파일 참조
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        case_sensitive = True

# 싱글톤 인스턴스
settings = LLMSettings()