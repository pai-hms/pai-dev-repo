# src/llm/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field

class LLMSettings(BaseSettings):
    """LLM 설정 관리"""
    
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini-2025-04-14", env="OPENAI_MODEL")
    OPENAI_TEMPERATURE: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    SYSTEM_PROMPT: str = Field(
        default="당신은 주가 계산을 도와주는 AI Agent입니다.", 
        env="SYSTEM_PROMPT"
    )
    
    class Config:
        env_file = ".env"

# 싱글톤
settings = LLMSettings()
