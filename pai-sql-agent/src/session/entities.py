"""
세션 엔티티 - 데이터베이스 매핑
"""
import logging
from datetime import datetime
from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean, JSON
from sqlalchemy.sql import func

from src.database.base import Base
from .domains import AgentSession

logger = logging.getLogger(__name__)


class AgentSessionEntity(Base):
    """SQL Agent 세션 엔티티"""
    
    __tablename__ = "agent_sessions"
    
    session_id = Column(String, primary_key=True)
    thread_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    
    # 시간
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity = Column(TIMESTAMP, default=func.now(), nullable=False)
    
    # 기본 정보
    message_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 메타데이터
    settings = Column(JSON, default={}, nullable=False)
    
    @classmethod
    def from_domain(cls, domain: AgentSession) -> 'AgentSessionEntity':
        return cls(
            session_id=domain.session_id,
            thread_id=domain.thread_id,
            title=domain.title,
            user_id=domain.user_id,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            last_activity=domain.last_activity,
            message_count=domain.message_count,
            is_active=domain.is_active,
            settings=domain.metadata or {}
        )
    
    def to_domain(self) -> AgentSession:
        return AgentSession(
            session_id=self.session_id,
            thread_id=self.thread_id,
            title=self.title,
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_activity=self.last_activity,
            message_count=self.message_count,
            is_active=self.is_active,
            metadata=self.settings or {}
        )
    
    def update_from_domain(self, domain: AgentSession):
        """도메인 모델로부터 엔티티 업데이트"""
        self.title = domain.title
        self.user_id = domain.user_id
        self.updated_at = domain.updated_at
        self.last_activity = domain.last_activity
        self.message_count = domain.message_count
        self.is_active = domain.is_active
        self.settings = domain.metadata or {}
    
    def primary_key(self) -> str:
        """주요 키 반환"""
        return self.session_id
    
    def __repr__(self):
        return f"<AgentSessionEntity(session_id='{self.session_id}', title='{self.title}', active={self.is_active})>"
