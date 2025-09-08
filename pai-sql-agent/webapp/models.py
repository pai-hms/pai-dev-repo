from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    stream: bool = False


class QueryResponse(BaseModel):
    success: bool
    message: str
    sql_queries: List[str] = []
    results: List[Dict[str, Any]] = []
    session_id: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None


class StreamChunk(BaseModel):
    type: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class TableInfoResponse(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]]
    description: Optional[str] = None


class AdminAreaSearchRequest(BaseModel):
    search_term: str


class AdminAreaSearchResponse(BaseModel):
    results: List[Dict[str, str]]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    database_connected: bool
    sgis_api_connected: bool


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
