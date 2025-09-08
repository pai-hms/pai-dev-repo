"""에이전트 설정."""

from pydantic import BaseSettings
from src.config import settings as app_settings


class AgentSettings(BaseSettings):
    """에이전트 설정 클래스."""
    
    # 데이터베이스 설정
    DATABASE_URL: str = app_settings.database_url
    
    # LLM 설정
    OPENAI_API_KEY: str = app_settings.openai_api_key or ""
    MODEL_NAME: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.0
    
    # 에이전트 설정
    MAX_ITERATIONS: int = 10
    ENABLE_TOOL_CALLING: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
agent_settings = AgentSettings()
