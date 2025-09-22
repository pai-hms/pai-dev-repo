"""
Agent 도메인 객체 정의
"""
import uuid
from dataclasses import dataclass
from typing import Optional, Literal

# 타입 정의
MODEL_TYPE = Literal["gemini-2.5-flash-lite", "gpt-4o-mini"]


@dataclass
class QueryParam:
    """쿼리 파라미터 도메인 객체 - 팩토리 메서드 패턴 적용"""
    
    # SQL Agent 기본 파라미터
    session_id: str = ""
    model: MODEL_TYPE = "gpt-4o-mini"
    
    @staticmethod
    def create_default(session_id: Optional[str] = None) -> "QueryParam":
        """기본 QueryParam 생성 - 팩토리 메서드"""
        return QueryParam(
            session_id=session_id or str(uuid.uuid4()),
            model="gpt-4o-mini"
        )
    
    @staticmethod
    def from_dict(data: dict) -> "QueryParam":
        """딕셔너리에서 QueryParam 생성 - 팩토리 메서드"""
        return QueryParam(
            session_id=data.get("session_id", str(uuid.uuid4())),
            model=data.get("model", "gpt-4o-mini")
        )
    
    @staticmethod
    def from_request(question: str, **kwargs) -> "QueryParam":
        """요청에서 QueryParam 생성 - 팩토리 메서드"""
        return QueryParam(
            session_id=kwargs.get("session_id", str(uuid.uuid4())),
            model=kwargs.get("model", "gpt-4o-mini")
        )
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "session_id": self.session_id,
            "model": self.model
        }


@dataclass
class AgentResponse:
    """에이전트 응답 도메인 객체"""
    
    content: str
    session_id: str
    message_id: Optional[str] = None
    response_type: str = "ai_message"
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "type": self.response_type,
            "content": self.content,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "metadata": self.metadata or {}
        }


@dataclass
class ToolCallInfo:
    """도구 호출 정보 도메인 객체"""
    
    tool_name: str
    session_id: str
    message_id: Optional[str] = None
    args: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "type": "tool_call",
            "content": self.tool_name,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "args": self.args or {}
        }


@dataclass
class ToolResult:
    """도구 실행 결과 도메인 객체"""
    
    tool_name: str
    content: str
    session_id: str
    message_id: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "type": "tool_result",
            "content": self.content,
            "tool_name": self.tool_name,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "success": self.success,
            "error": self.error
        }
