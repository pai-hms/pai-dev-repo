"""
Database Settings - 데이터베이스 전용 설정
기존 agent/settings.py에서 DB 관련 설정을 분리
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from src.agent.settings import get_settings


class DatabaseSettings(BaseSettings):
    """데이터베이스 전용 설정"""
    
    # 기본 연결 설정 (기존 AgentSettings와 호환)
    DB_TYPE: str = Field(default="postgresql", description="데이터베이스 타입")
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@postgres:5432/pai_sql_agent",
        description="데이터베이스 연결 URL"
    )
    
    # 연결 풀 설정
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=50, description="연결 풀 크기")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100, description="최대 오버플로우")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, le=300, description="연결 타임아웃 (초)")
    DB_POOL_RECYCLE: int = Field(default=3600, ge=300, description="연결 재활용 시간 (초)")
    
    # 세션 설정
    DB_ECHO: bool = Field(default=False, description="SQL 로깅 여부")
    DB_AUTOCOMMIT: bool = Field(default=False, description="자동 커밋 여부")
    DB_AUTOFLUSH: bool = Field(default=True, description="자동 플러시 여부")
    DB_EXPIRE_ON_COMMIT: bool = Field(default=False, description="커밋 시 만료 여부")
    
    # 성능 최적화 설정
    DB_POOL_PRE_PING: bool = Field(default=True, description="연결 사전 핑 여부")
    DB_POOL_RESET_ON_RETURN: str = Field(default="commit", description="반환 시 리셋 방식")
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False


def get_database_settings() -> DatabaseSettings:
    """데이터베이스 설정 인스턴스 반환 - 기존 AgentSettings와 호환"""
    # 기존 AgentSettings에서 DATABASE_URL 가져오기
    try:
        agent_settings = get_settings()
        
        # 기존 설정의 DATABASE_URL 사용
        return DatabaseSettings(DATABASE_URL=agent_settings.DATABASE_URL)
    except Exception:
        # Fallback: 기본 설정 사용
        return DatabaseSettings()
