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


class ToolInfo(BaseModel):
    """도구 실행 정보"""
    tool_name: str
    tool_function: str
    tool_description: str
    arguments: Dict[str, Any]
    execution_order: int
    success: bool
    result_preview: Optional[str] = None
    error_message: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    message: str
    sql_queries: List[str] = []
    query_results: List[Dict[str, Any]] = []
    tools_used: List[ToolInfo] = []
    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """스트리밍 응답 청크"""
    type: str  # token, tool_start, tool_end, node_update, state_update, complete, error
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionInfo(BaseModel):
    """세션 정보"""
    session_id: str
    thread_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool


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


# 추가된 모델들 (data.py에서 필요한 모델들)

class DatabaseSchemaResponse(BaseModel):
    """데이터베이스 스키마 응답"""
    tables: List[Dict[str, Any]]
    total_tables: int
    database_name: str


class TableSchemaResponse(BaseModel):
    """테이블 스키마 응답"""
    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]] = []
    constraints: List[Dict[str, Any]] = []
