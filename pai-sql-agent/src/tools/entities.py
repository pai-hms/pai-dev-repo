"""
DB 테이블과 매핑되는 SQLAlchemy 엔티티
데이터베이스 접근 계층
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Float
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.sql import func
from src.database.base import Base
from src.tools.domains import ToolAgent, ToolAgentType, ToolAgentStatus


class ToolAgentEntity(Base):
    """Tool Agent 데이터베이스 엔티티"""
    
    __tablename__ = "tool_agents"
    
    # 기본 필드
    tool_agent_id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, nullable=False, index=True)
    agent_type = Column(SQLEnum(ToolAgentType), nullable=False)
    
    # 설정 및 상태
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(SQLEnum(ToolAgentStatus), nullable=False, default=ToolAgentStatus.ACTIVE)
    
    # 메타데이터
    name = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    
    # 성능 및 사용량 정보
    usage_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)
    avg_response_time = Column(Float, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_domain(self) -> ToolAgent:
        """엔티티를 도메인 모델로 변환"""
        return ToolAgent(
            tool_agent_id=self.tool_agent_id,
            chatbot_id=self.chatbot_id,
            agent_type=self.agent_type,
            config=self.config or {},
            is_active=self.is_active,
            status=self.status,
            name=self.name,
            description=self.description,
            version=self.version,
            usage_count=self.usage_count,
            last_used_at=self.last_used_at,
            avg_response_time=self.avg_response_time,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
    
    @classmethod
    def from_domain(cls, domain: ToolAgent) -> 'ToolAgentEntity':
        """도메인 모델에서 엔티티 생성"""
        return cls(
            tool_agent_id=domain.tool_agent_id,
            chatbot_id=domain.chatbot_id,
            agent_type=domain.agent_type,
            config=domain.config,
            is_active=domain.is_active,
            status=domain.status,
            name=domain.name,
            description=domain.description,
            version=domain.version,
            usage_count=domain.usage_count,
            last_used_at=domain.last_used_at,
            avg_response_time=domain.avg_response_time,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )