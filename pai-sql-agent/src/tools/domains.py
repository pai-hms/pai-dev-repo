"""
Tool Agent 도메인 모델 (도메인 계층)
도메인 주도 설계(DDD)에 따른 핵심 엔티티
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ToolAgentType(Enum):
    """Tool Agent 타입"""
    SQL_AGENT = "sql_agent"
    WEB_SEARCH = "web_search"
    FILE_PROCESSOR = "file_processor"
    API_CONNECTOR = "api_connector"
    # 향후 확장 가능한 도구들
    # PLOTLY_VIS_AGENT = "plotly_vis_agent" 
    # RAG_RETRIEVER = "rag_retriever"
    # EMAIL_SENDER = "email_sender"


class ToolAgentStatus(Enum):
    """Tool Agent 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class ToolAgent:
    """Tool Agent 도메인 엔티티"""
    
    # 기본 식별자
    tool_agent_id: Optional[int]
    chatbot_id: int
    agent_type: ToolAgentType
    
    # 설정 및 상태
    config: Dict[str, Any]
    is_active: bool = True
    status: ToolAgentStatus = ToolAgentStatus.ACTIVE
    
    # 메타데이터
    name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    
    # 성능 및 사용량 정보
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    avg_response_time: Optional[float] = None
    
    # 타임스탬프
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def id(self) -> Optional[int]:
        """ID 속성 (하위 호환성)"""
        return self.tool_agent_id
    
    @property
    def is_sql_agent(self) -> bool:
        """SQL Agent 여부 확인"""
        return self.agent_type == ToolAgentType.SQL_AGENT
    
    @property
    def is_available(self) -> bool:
        """사용 가능 여부 확인"""
        return self.is_active and self.status == ToolAgentStatus.ACTIVE
    
    def activate(self):
        """도구 활성화"""
        self.is_active = True
        self.status = ToolAgentStatus.ACTIVE
        self.updated_at = datetime.now()
    
    def deactivate(self):
        """도구 비활성화"""
        self.is_active = False
        self.status = ToolAgentStatus.INACTIVE
        self.updated_at = datetime.now()
    
    def set_maintenance(self):
        """유지보수 모드 설정"""
        self.status = ToolAgentStatus.MAINTENANCE
        self.updated_at = datetime.now()
    
    def set_error(self):
        """오류 상태 설정"""
        self.status = ToolAgentStatus.ERROR
        self.updated_at = datetime.now()
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        self.config.update(new_config)
        self.updated_at = datetime.now()
    
    def record_usage(self, response_time: float = None):
        """사용 기록 업데이트"""
        self.usage_count += 1
        self.last_used_at = datetime.now()
        
        if response_time is not None:
            if self.avg_response_time is None:
                self.avg_response_time = response_time
            else:
                # 이동 평균 계산
                self.avg_response_time = (self.avg_response_time * 0.8) + (response_time * 0.2)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """설정값 안전하게 가져오기"""
        return self.config.get(key, default)
    
    def validate_config(self) -> bool:
        """설정 유효성 검증"""
        if self.agent_type == ToolAgentType.SQL_AGENT:
            required_keys = ["database_url", "allowed_tables"]
            return all(key in self.config for key in required_keys)
        
        elif self.agent_type == ToolAgentType.WEB_SEARCH:
            required_keys = ["search_engine", "api_key"]
            return all(key in self.config for key in required_keys)
        
        elif self.agent_type == ToolAgentType.API_CONNECTOR:
            required_keys = ["base_url", "auth_type"]
            return all(key in self.config for key in required_keys)
        
        # 기본적으로는 유효한 것으로 간주
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "tool_agent_id": self.tool_agent_id,
            "chatbot_id": self.chatbot_id,
            "agent_type": self.agent_type.value,
            "config": self.config,
            "is_active": self.is_active,
            "status": self.status.value,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "avg_response_time": self.avg_response_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolAgent':
        """딕셔너리에서 생성"""
        return cls(
            tool_agent_id=data.get("tool_agent_id"),
            chatbot_id=data["chatbot_id"],
            agent_type=ToolAgentType(data["agent_type"]),
            config=data.get("config", {}),
            is_active=data.get("is_active", True),
            status=ToolAgentStatus(data.get("status", "active")),
            name=data.get("name"),
            description=data.get("description"),
            version=data.get("version", "1.0.0"),
            usage_count=data.get("usage_count", 0),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
            avg_response_time=data.get("avg_response_time"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


@dataclass
class ToolAgentExecutionResult:
    """Tool Agent 실행 결과"""
    
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_success(self) -> bool:
        """성공 여부"""
        return self.success
    
    @property
    def has_error(self) -> bool:
        """오류 여부"""
        return not self.success or self.error_message is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata or {}
        }


# 도메인 서비스용 인터페이스들
class ToolAgentRepository:
    """Tool Agent Repository 인터페이스"""
    
    async def find_by_id(self, tool_agent_id: int) -> Optional[ToolAgent]:
        """ID로 조회"""
        raise NotImplementedError
    
    async def find_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """챗봇 ID로 조회"""
        raise NotImplementedError
    
    async def find_active_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """활성 상태만 조회"""
        raise NotImplementedError
    
    async def create(self, tool_agent: ToolAgent) -> ToolAgent:
        """생성"""
        raise NotImplementedError
    
    async def update(self, tool_agent: ToolAgent) -> ToolAgent:
        """업데이트"""
        raise NotImplementedError
    
    async def delete(self, tool_agent_id: int) -> bool:
        """삭제"""
        raise NotImplementedError