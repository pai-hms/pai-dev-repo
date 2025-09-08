"""Pydantic models for API requests and responses."""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Request model for asking questions to the agent."""
    question: str = Field(..., description="User question about budget or census data")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")


class AgentResponse(BaseModel):
    """Response model for agent answers."""
    success: bool
    response: Optional[str] = None
    thread_id: Optional[str] = None
    iteration_count: Optional[int] = None
    sql_query: Optional[str] = None
    query_result: Optional[str] = None
    error: Optional[str] = None


class StreamChunk(BaseModel):
    """Model for streaming response chunks."""
    type: str = Field(..., description="Type of chunk: 'agent', 'tool', 'error', 'final'")
    content: Dict[str, Any] = Field(..., description="Chunk content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BudgetItemResponse(BaseModel):
    """Response model for budget items."""
    id: int
    year: int
    category_code: str
    item_name: str
    budget_amount: float
    executed_amount: Optional[float]
    execution_rate: Optional[float]
    department: Optional[str]
    sub_department: Optional[str]


class PopulationDataResponse(BaseModel):
    """Response model for population data."""
    id: int
    year: int
    region_code: str
    region_name: str
    total_population: int
    male_population: Optional[int]
    female_population: Optional[int]
    household_count: Optional[int]


class QueryHistoryResponse(BaseModel):
    """Response model for query history."""
    id: int
    user_question: str
    generated_sql: str
    execution_result: Optional[str]
    success: bool
    execution_time_ms: Optional[int]
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    database_connected: bool
    agent_ready: bool
