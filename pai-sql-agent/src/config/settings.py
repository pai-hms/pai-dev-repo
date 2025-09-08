"""
애플리케이션 설정 관리
데이터 주권 원칙에 따라 설정 데이터의 제어권을 담당
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI 설정
    openai_api_key: str = Field(description="OpenAI API 키")
    
    # SGIS API 설정
    sgis_access_key: str = Field(description="SGIS 액세스 키")
    sgis_secret_key: str = Field(description="SGIS 시크릿 키")
    sgis_base_url: str = Field(
        default="https://sgisapi.kostat.go.kr/OpenAPI3",
        description="SGIS API 기본 URL"
    )
    
    # 데이터베이스 설정
    database_url: str = Field(
        default="postgresql://pai_user:pai_password@localhost:5432/pai_sql_agent",
        description="데이터베이스 연결 URL"
    )
    
    # 애플리케이션 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    debug: bool = Field(default=False, description="디버그 모드")
    
    # API 설정
    api_timeout: int = Field(default=30, description="API 타임아웃 (초)")
    max_retries: int = Field(default=3, description="최대 재시도 횟수")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 싱글톤 패턴으로 설정 인스턴스 관리
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings