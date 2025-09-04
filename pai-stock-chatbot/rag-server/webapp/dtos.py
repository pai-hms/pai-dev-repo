# rag-server/webapp/dtos.py
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    """FastAPI의 모든 Request, Response 모델에 CamelCase를 적용"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

def convert_to_camel_case(data: dict) -> dict:
    """딕셔너리의 키를 카멜케이스로 변환합니다."""
    result = {}
    for key, value in data.items():
        # 스네이크 케이스를 카멜케이스로 변환
        camel_key = ''.join(word.capitalize() if i > 0 else word.lower() 
                            for i, word in enumerate(key.split('_')))
        
        # 중첩된 딕셔너리가 있는 경우 재귀적으로 처리
        if isinstance(value, dict):
            result[camel_key] = convert_to_camel_case(value)
        else:
            result[camel_key] = value
    return result

def convert_to_snake_case(data: dict) -> dict:
    """딕셔너리의 키를 스네이크 케이스로 변환합니다."""
    result = {}
    for key, value in data.items():
        # 카멜케이스를 스네이크 케이스로 변환
        snake_key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', key).lower()
        
        # 중첩된 딕셔너리가 있는 경우 재귀적으로 처리
        if isinstance(value, dict):
            result[snake_key] = convert_to_snake_case(value)
        else:
            result[snake_key] = value
    return result

# ===== 기본 응답 DTO =====
class OkDTO(CamelModel):
    """성공 응답"""
    ok: bool = Field(default=True, description="성공 여부")

class ErrorResponseDTO(CamelModel):
    """에러 응답 DTO"""
    message: str = Field(description="에러 메시지", examples=["요청 처리 중 오류가 발생했습니다"])
    code: str = Field(description="에러 코드", examples=["InvalidRequestException"])
    trace_id: Optional[str] = Field(None, description="추적 ID", examples=["abc12345"])

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

# ===== 주식 관련 DTO =====
class StockPriceDTO(CamelModel):
    """주식 가격 정보 DTO"""
    symbol: str = Field(description="주식 심볼", examples=["AAPL"])
    price: float = Field(description="현재 가격", examples=[150.25])
    change: float = Field(description="변동액", examples=[2.5])
    change_percent: float = Field(description="변동률(%)", examples=[1.69])
    currency: str = Field(description="통화", examples=["USD"], default="USD")
    timestamp: str = Field(description="조회 시간", examples=["2024-01-01T12:00:00Z"])

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """주식 심볼 검증"""
        if not v or not v.strip():
            raise ValueError("주식 심볼은 필수입니다")
        
        # 주식 심볼 형식 검증 (영문 대문자, 숫자, 점)
        if not re.match(r'^[A-Z0-9.]+$', v.upper()):
            raise ValueError("올바른 주식 심볼 형식이 아닙니다")
        
        return v.upper().strip()

    @staticmethod
    def from_domain(stock_data: dict) -> "StockPriceDTO":
        """주식 데이터에서 DTO로 변환"""
        return StockPriceDTO(
            symbol=stock_data["symbol"],
            price=stock_data["price"],
            change=stock_data.get("change", 0.0),
            change_percent=stock_data.get("change_percent", 0.0),
            currency=stock_data.get("currency", "USD"),
            timestamp=stock_data.get("timestamp", datetime.now().isoformat())
        )

# ===== 계산 관련 DTO =====
class CalculationRequest(CamelModel):
    """계산 요청 DTO"""
    expression: str = Field(description="계산 표현식", examples=["100 * 1.5", "2 + 3 * 4"])

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        """계산 표현식 검증"""
        if not v or not v.strip():
            raise ValueError("계산 표현식이 비어있습니다")
        
        # 안전한 계산을 위한 기본 검증 (숫자, 연산자, 공백만 허용)
        if not re.match(r'^[0-9+\-*/().\s]+$', v):
            raise ValueError("허용되지 않는 문자가 포함되어 있습니다")
        
        return v.strip()

class CalculationResponse(CamelModel):
    """계산 응답 DTO"""
    expression: str = Field(description="원본 표현식", examples=["100 * 1.5"])
    result: float = Field(description="계산 결과", examples=[150.0])
    formatted_result: str = Field(description="포맷된 결과", examples=["150.0"])

    @staticmethod
    def from_calculation(expression: str, result: float) -> "CalculationResponse":
        """계산 결과에서 DTO로 변환"""
        return CalculationResponse(
            expression=expression,
            result=result,
            formatted_result=f"{result:,.2f}".rstrip('0').rstrip('.')
        )

# ===== 페이지네이션 관련 DTO =====
class PaginationDTO(CamelModel):
    """페이지네이션 정보"""
    page: int = Field(1, description="현재 페이지", ge=1, examples=[1])
    size: int = Field(20, description="페이지 크기", ge=1, le=100, examples=[20])
    total: int = Field(description="전체 항목 수", ge=0, examples=[100])
    total_pages: int = Field(description="전체 페이지 수", ge=0, examples=[5])

    @staticmethod
    def create(page: int, size: int, total: int) -> "PaginationDTO":
        """페이지네이션 정보 생성"""
        total_pages = (total + size - 1) // size if total > 0 else 0
        return PaginationDTO(
            page=page,
            size=size,
            total=total,
            total_pages=total_pages
        )

class ListResponseDTO(CamelModel):
    """리스트 응답 기본 구조"""
    data: List[Any] = Field(description="데이터 목록")
    pagination: Optional[PaginationDTO] = Field(None, description="페이지네이션 정보")

    @staticmethod
    def create_simple(data: List[Any]) -> "ListResponseDTO":
        """간단한 리스트 응답 생성"""
        return ListResponseDTO(data=data, pagination=None)

    @staticmethod
    def create_paginated(data: List[Any], page: int, size: int, total: int) -> "ListResponseDTO":
        """페이지네이션 리스트 응답 생성"""
        return ListResponseDTO(
            data=data,
            pagination=PaginationDTO.create(page, size, total)
        )

# ===== 사용자 질문 DTO =====
class UserQuestionDTO(CamelModel):
    """사용자 질문 정보를 담는 DTO"""
    query: str = Field(
        description="사용자 메시지",
        examples=["AAPL 주가는 얼마인가요?", "100 곱하기 1.5는?"],
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """질문 검증"""
        if not v or not v.strip():
            raise ValueError("질문이 비어있습니다")
        
        if len(v.strip()) > 500:
            raise ValueError("질문은 500자를 초과할 수 없습니다")
        
        return v.strip()