# rag-server/webapp/dtos.py
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    """FastAPI의 모든 Request, Response 모델에 CamelCase를 적용"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

# ===== 채팅 관련 DTO =====
class ChatRequest(CamelModel):
    """채팅 요청 DTO"""
    message: str = Field(description="사용자 메시지", examples=["AAPL 주가 알려줘"])
    thread_id: str = Field(description="스레드 ID", examples=["thread_123"])

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """메시지 검증"""
        if not v or not v.strip():
            raise ValueError("메시지가 비어있습니다")
        
        if len(v.strip()) > 1000:
            raise ValueError("메시지는 1000자를 초과할 수 없습니다")
        
        # XSS 방지를 위한 기본 검증
        if re.search(r'[<>]', v):
            raise ValueError("허용되지 않는 문자가 포함되어 있습니다")
        
        return v.strip()

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, v: str) -> str:
        """스레드 ID 검증"""
        if not v or not v.strip():
            raise ValueError("스레드 ID가 비어있습니다")
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("스레드 ID는 영문, 숫자, _, -만 사용 가능합니다")
        
        if len(v) > 50:
            raise ValueError("스레드 ID는 50자를 초과할 수 없습니다")
        
        return v.strip()

    @model_validator(mode='after')
    def validate_request(self):
        """전체 요청 검증"""
        # 비즈니스 로직 검증 예시
        if self.message.lower() in ['test', '테스트'] and not self.thread_id.startswith('test_'):
            raise ValueError("테스트 메시지는 test_ 접두사가 있는 스레드에서만 사용 가능합니다")
        
        return self

# ===== 세션 관련 DTO =====
class SessionInfoDTO(CamelModel):
    """세션 정보 DTO"""
    thread_id: str = Field(description="스레드 ID", examples=["thread_123"])
    created_at: str = Field(description="생성 시간", examples=["2024-01-01T00:00:00Z"])
    last_accessed: str = Field(description="마지막 접근 시간", examples=["2024-01-01T01:00:00Z"])
    message_count: int = Field(description="메시지 수", examples=[5], ge=0)
    active: bool = Field(description="활성 상태", examples=[True])

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, v: str) -> str:
        if not v:
            raise ValueError("스레드 ID는 필수입니다")
        return v

    @field_validator("created_at", "last_accessed")
    @classmethod
    def validate_datetime_format(cls, v: str) -> str:
        """날짜 형식 검증"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("올바른 ISO 형식의 날짜가 아닙니다")
        return v

    @staticmethod
    def from_domain(session_data: dict) -> "SessionInfoDTO":
        """도메인 데이터 변환 시 추가 검증"""
        if not session_data:
            raise ValueError("세션 데이터가 없습니다")
        
        # 필수 필드 검증
        required_fields = ["thread_id", "created_at", "last_accessed"]
        for field in required_fields:
            if field not in session_data:
                raise ValueError(f"필수 필드 {field}가 누락되었습니다")
        
        return SessionInfoDTO(
            thread_id=session_data["thread_id"],
            created_at=session_data["created_at"],
            last_accessed=session_data["last_accessed"],
            message_count=session_data.get("message_count", 0),
            active=session_data.get("active", True),
        )

class SessionResponseDTO(CamelModel):
    """세션 응답 DTO"""
    message: str = Field(description="응답 메시지", examples=["세션이 성공적으로 종료되었습니다"])
    thread_id: Optional[str] = Field(None, description="스레드 ID", examples=["thread_123"])

    @staticmethod
    def success(message: str, thread_id: Optional[str] = None) -> "SessionResponseDTO":
        """성공 응답 생성 헬퍼"""
        return SessionResponseDTO(message=message, thread_id=thread_id)

class ActiveSessionsDTO(CamelModel):
    """활성 세션 목록 DTO"""
    sessions: List[Dict[str, Any]] = Field(description="세션 목록", examples=[[]])
    total_count: int = Field(description="전체 세션 수", examples=[0], ge=0)

    @staticmethod
    def from_domain(sessions: List[dict]) -> "ActiveSessionsDTO":
        """도메인 데이터에서 DTO로 변환"""
        return ActiveSessionsDTO(
            sessions=sessions or [],
            total_count=len(sessions) if sessions else 0
        )