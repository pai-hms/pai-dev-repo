"""
SQL Agent 설정 관리 - 비동기 통일 버전
"""
import os
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
    
    # PostgresSaver 설정 - DATABASE_URL과 동일하게 사용
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
    
    # # SGIS API 설정 (선택적)
    # sgis_service_id: Optional[str] = Field(default=None, description="SGIS 서비스 ID")
    # sgis_security_key: Optional[str] = Field(default=None, description="SGIS 보안 키")
    
    # class Config:
    #     # PostgreSQL 관련 환경변수도 자동으로 읽어옴
    #     env_file = ".env"
    #     env_file_encoding = "utf-8"
    
    # def has_sgis_config(self) -> bool:
    #     """SGIS 설정이 모두 있는지 확인"""
    #     return bool(self.sgis_service_id and self.sgis_security_key)

    # PostgresSaver URL을 DATABASE_URL과 동일하게 설정
    @property 
    def postgres_url(self) -> str:
        """PostgresSaver용 DATABASE URL - DATABASE_URL과 동일하게 사용"""
        return self.DATABASE_URL


# 비동기 팩토리 함수
async def get_agent_settings() -> AgentSettings:
    """비동기 Agent 설정 반환"""
    return AgentSettings()


# 동기 팩토리 함수 (호환성)
def get_agent_settings_sync() -> AgentSettings:
    """동기 Agent 설정 반환"""
    return AgentSettings()