"""
LLM 설정 클래스
기존 agent/settings.py와 호환되도록 구현
"""
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM 관련 설정"""
    
    # 기본 모델 설정
    DEFAULT_MODEL_KEY: str = Field(default="gpt-4o-mini")
    
    # API 키들 (기존 agent/settings.py와 호환)
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API 키")
    GOOGLE_API_KEY: str = Field(default="", description="Google API 키")
    
    # 공통 런타임 옵션
    MAX_CONCURRENCY: int = Field(default=10, description="최대 동시 연결 수")
    REQUEST_TIMEOUT: int = Field(default=30, description="요청 타임아웃 (초)")
    
    
    # LLM 모델 설정
    temperature: float = Field(default=0.1, description="LLM 창의성 수준")
    max_tokens: int = Field(default=2000, description="최대 토큰 수")
    streaming: bool = Field(default=True, description="스트리밍 사용 여부")
    
    class Config:
        env_prefix = "LLM_"
