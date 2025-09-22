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
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API 키")
    google_api_key: Optional[str] = Field(default=None, description="Google Gemini API 키")
    
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
    
    # 에이전트 동작 설정
    max_iterations: int = Field(default=3, description="최대 반복 횟수")
    timeout_seconds: int = Field(default=30, description="타임아웃 시간 (초)")
    max_result_rows: int = Field(default=50, description="최대 결과 행 수")
    query_timeout: int = Field(default=10, description="쿼리 타임아웃 (초)")
    
    # 체크포인터 설정 (기존 유지)
    enable_checkpointer: bool = Field(default=True, description="체크포인터 활성화")
    
    # 스트리밍 설정
    streaming_enabled: bool = Field(default=True, description="스트리밍 활성화")
    token_delay_ms: int = Field(default=50, description="토큰 간 지연시간 (밀리초)")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    debug: bool = Field(default=False, description="디버그 모드")
    
    # API 설정 (통합)
    api_timeout: int = Field(default=30, description="API 타임아웃 (초)")
    max_retries: int = Field(default=3, description="최대 재시도 횟수")
    
    # SGIS API 설정 (선택적)
    sgis_service_id: Optional[str] = Field(default=None, description="SGIS 서비스 ID")
    sgis_security_key: Optional[str] = Field(default=None, description="SGIS 보안 키")
    
    # 환경변수 설정
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_ignore_empty": True,
        "extra": "ignore"
    }
    
    def has_sgis_config(self) -> bool:
        """SGIS 설정이 모두 있는지 확인"""
        return bool(self.sgis_service_id and self.sgis_security_key)
    
    @property
    def sgis_configured(self) -> bool:
        """SGIS API 설정 여부 확인 (호환성)"""
        return self.has_sgis_config()

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


# 동기 팩토리 함수 (호환성)
def get_agent_settings_sync() -> AgentSettings:
    """동기 Agent 설정 반환"""
    global _settings
    if _settings is None:
        _settings = AgentSettings()
    return _settings


# config/settings.py 호환성을 위한 별칭 함수들
def get_settings() -> AgentSettings:
    """기존 config/settings.py 호환성을 위한 별칭"""
    return get_agent_settings_sync()


# 타입 별칭 (호환성)
Settings = AgentSettings