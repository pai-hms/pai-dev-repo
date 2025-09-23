"""
통합 설정 관리 - 전체 애플리케이션 설정
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class AgentSettings(BaseSettings):
    """통합 애플리케이션 설정 클래스"""
    
    # LLM API 설정
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API 키")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API 키")
    
    # 데이터베이스 설정 (통합)
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@postgres:5432/pai_sql_agent",
        description="데이터베이스 연결 URL (Agent State 및 일반 데이터)",
    )
    
    @property
    def database_url(self) -> str:
        """기존 코드 호환성을 위한 소문자 속성"""
        return self.DATABASE_URL
    
    # PostgresSaver 설정
    enable_memory: bool = Field(default=True, description="메모리(PostgresSaver) 활성화")
    
    # Context Length 관리 설정
    TRIM_MAX_TOKENS: int = Field(
        default=60000,
        ge=1000,
        le=200000,
        description="메시지 트리밍 최대 토큰 수 (Agent 레벨)"
    )
    
    DOCUMENT_MAX_TOKENS: int = Field(
        default=10000,
        ge=1000,
        le=50000,
        description="문서 컨텍스트 최대 토큰 수 (Tool 레벨)"
    )
    
    ENABLE_CONTEXT_FILTERING: bool = Field(
        default=True,
        description="지능형 컨텍스트 필터링 활성화"
    )
    
    # PostgresSaver 연결 풀 설정
    POSTGRES_MAX_CONNECTIONS: int = Field(
        default=10,
        ge=1,
        le=50,
        description="PostgresSaver 최대 연결 수"
    )
    
    POSTGRES_AUTOCOMMIT: bool = Field(
        default=True,
        description="PostgresSaver 자동 커밋"
    )
    
    POSTGRES_PREPARE_THRESHOLD: int = Field(
        default=0,
        ge=0,
        description="Prepared Statement 임계값 (0=비활성화)"
    )
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    debug: bool = Field(default=False, description="디버그 모드")
    
    # 환경변수 설정
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_ignore_empty": True,
        "extra": "ignore"
    }
    
    # SGIS 관련 메서드들 제거됨 (미사용)

    # PostgresSaver URL을 DATABASE_URL과 동일하게 설정
    @property 
    def postgres_url(self) -> str:
        """PostgresSaver용 DATABASE URL - DATABASE_URL과 동일하게 사용"""
        return self.DATABASE_URL


# 글로벌 설정 객체 (싱글톤 패턴)
_settings: Optional[AgentSettings] = None


# 비동기 팩토리 함수
async def get_agent_settings() -> AgentSettings:
    """비동기 Agent 설정 반환"""
    global _settings
    if _settings is None:
        _settings = AgentSettings()
    return _settings


# 동기 팩토리 함수
def get_settings() -> AgentSettings:
    """동기 Agent 설정 반환 - 전체 애플리케이션에서 사용"""
    global _settings
    if _settings is None:
        _settings = AgentSettings()
    return _settings