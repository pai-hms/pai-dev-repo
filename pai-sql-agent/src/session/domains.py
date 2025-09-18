"""
세션 도메인 모델
멀티턴 대화를 위한 세션 도메인 모델
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class AgentSession:
    """SQL Agent 세션 모델"""
    
    session_id: str
    thread_id: str
    title: str
    user_id: Optional[str] = None
    
    # 시간 정보
    created_at: datetime = None
    updated_at: datetime = None
    last_activity: datetime = None
    
    # 기본 정보
    message_count: int = 0
    is_active: bool = True
    
    # 메타데이터 (JSON)
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
        if self.last_activity is None:
            self.last_activity = now
    
    @classmethod
    def new(cls, title: str, user_id: Optional[str] = None, custom_thread_id: Optional[str] = None) -> 'AgentSession':
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        thread_id = custom_thread_id or f"thread_{session_id[:8]}"
        
        return cls(
            session_id=session_id,
            thread_id=thread_id,
            title=title,
            user_id=user_id
        )
    
    @classmethod
    def create_new(cls, title: str, user_id: Optional[str] = None, custom_thread_id: Optional[str] = None) -> 'AgentSession':
        """별칭"""
        return cls.new(title=title, user_id=user_id, custom_thread_id=custom_thread_id)
    
    def update_activity(self):
        """활동 시간 업데이트"""
        now = datetime.now()
        self.updated_at = now
        self.last_activity = now
    
    def increment_message_count(self):
        """메시지 카운트 증가"""
        self.message_count += 1
        self.update_activity()


@dataclass
class SessionContext:
    """세션 컨텍스트"""
    
    session: AgentSession
    current_message: str
    conversation_history: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
