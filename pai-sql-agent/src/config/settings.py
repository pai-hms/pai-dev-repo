"""
애플리케이션 설정 관리
환경 변수 및 설정값을 중앙 집중식으로 관리하는 모듈
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI 설정
    openai_api_key: str = Field(description="OpenAI API 키")

    # 데이터베이스 설정
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/pai_sql_agent",
        description="데이터베이스 연결 URL"
    )
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    debug: bool = Field(default=False, description="디버그 모드")
    
    # API 설정
    api_timeout: int = Field(default=30, description="API 타임아웃 (초)")
    max_retries: int = Field(default=3, description="최대 재시도 횟수")
    
    @property
    def sgis_configured(self) -> bool:
        """SGIS API 설정 여부 확인"""
        return bool(self.sgis_service_id and self.sgis_security_key)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # 환경변수 없어도 오류가 발생하지 않도록 설정
        "env_ignore_empty": True,
        # 추가 필드 허용
        "extra": "ignore"
    }


# 글로벌 설정 객체 (싱글톤 패턴)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """설정 객체 반환 (싱글톤)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings