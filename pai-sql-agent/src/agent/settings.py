"""
SQL Agent 설정 관리 - 비동기 통일 버전
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class AgentSettings(BaseSettings):
    """Agent 설정 클래스"""
    
    # 데이터베이스 설정
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        description="Agent State를 관리하는 DATABASE URL",
    )
    
    # 에이전트 동작 설정
    max_iterations: int = Field(default=3, description="최대 반복 횟수")
    timeout_seconds: int = Field(default=30, description="타임아웃 시간 (초)")
    max_result_rows: int = Field(default=50, description="최대 결과 행 수")
    query_timeout: int = Field(default=10, description="쿼리 타임아웃 (초)")
    
    # 체크포인터 설정
    enable_checkpointer: bool = Field(default=True, description="체크포인터 활성화")
    
    # 스트리밍 설정
    streaming_enabled: bool = Field(default=True, description="스트리밍 활성화")
    token_delay_ms: int = Field(default=50, description="토큰 간 지연시간 (밀리초)")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    
    # # SGIS API 설정 (선택적)
    # sgis_service_id: Optional[str] = Field(default=None, description="SGIS 서비스 ID")
    # sgis_security_key: Optional[str] = Field(default=None, description="SGIS 보안 키")
    # sgis_access_token: Optional[str] = Field(default=None, description="SGIS 액세스 토큰")
    # sgis_secret_key: Optional[str] = Field(default=None, description="SGIS 시크릿 키")
    
    # 캐시 설정
    enable_cache: bool = Field(default=True, description="캐시 활성화")
    cache_ttl_seconds: int = Field(default=300, description="캐시 TTL (초)")
    
    @property
    def checkpoint_db_url(self) -> Optional[str]:
        """체크포인터용 DB URL"""
        return self.DATABASE_URL if self.enable_checkpointer else None
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL
    
    # @property
    # def sgis_configured(self) -> bool:
    #     """SGIS API 설정 여부"""
    #     return bool(self.sgis_service_id and self.sgis_security_key)


# 비동기 팩토리 함수
async def create_agent_settings() -> AgentSettings:
    """Agent 설정 생성 (비동기)"""
    return AgentSettings()


# 전역 설정 (비동기 싱글톤)
_settings: Optional[AgentSettings] = None


async def get_agent_settings() -> AgentSettings:
    """Agent 설정 반환 (비동기 싱글톤)"""
    global _settings
    if _settings is None:
        _settings = await create_agent_settings()
    return _settings