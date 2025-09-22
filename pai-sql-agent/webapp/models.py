from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # 하위 호환성
    thread_id: Optional[str] = None   # 멀티턴 대화용
    stream: bool = False
    stream_mode: Optional[str] = "messages"  # LangGraph 스트리밍 모드: messages, updates, values, all
    request_type: Optional[str] = None  # 요청 분류 타입: sql, general, None=자동분류


class StreamChunk(BaseModel):
    """스트리밍 응답 청크"""
    type: str  # token, tool_start, tool_end, node_update, state_update, complete, error
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """오류 응답"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: Optional[str] = None
    services: Dict[str, str] = Field(default_factory=dict)
    database_connected: Optional[bool] = None


