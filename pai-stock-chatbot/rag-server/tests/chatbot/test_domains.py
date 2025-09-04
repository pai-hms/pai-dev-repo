# tests/chat_session/test_domains.py
import pytest
from datetime import datetime, timedelta
import uuid

from src.chat_session.domains import ChatSession, ChatMessage


class TestChatSession:
    """ChatSession 도메인 객체 테스트"""

    def test_chat_session_creation_with_new(self):
        """ChatSession.new() 생성 테스트"""
        # given
        title = "테스트 세션"
        chatbot_id = "test_bot"
        
        # when
        session = ChatSession.new(title=title, chatbot_id=chatbot_id)
        
        # then
        assert session.title == title
        assert session.chatbot_id == chatbot_id
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.is_active is True
        assert session.message_count == 0
        assert session.metadata == {}
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_accessed, datetime)

    def test_chat_session_with_default_chatbot_id(self):
        """기본 챗봇 ID로 세션 생성 테스트"""
        # when
        session = ChatSession.new("테스트 세션")
        
        # then
        assert session.chatbot_id == "default"

    def test_chat_session_unique_ids(self):
        """세션 ID 유일성 테스트"""
        # when
        session1 = ChatSession.new("세션 1")
        session2 = ChatSession.new("세션 2")
        
        # then
        assert session1.session_id != session2.session_id

    def test_chat_session_valid_uuid(self):
        """세션 ID가 유효한 UUID인지 테스트"""
        # when
        session = ChatSession.new("테스트 세션")
        
        # then
        # UUID 형식인지 확인
        uuid.UUID(session.session_id)  # 유효하지 않으면 ValueError 발생

    def test_increment_message_count(self):
        """메시지 카운트 증가 테스트"""
        # given
        session = ChatSession.new("테스트 세션")
        initial_count = session.message_count
        initial_time = session.last_accessed
        
        # when
        session.increment_message_count()
        
        # then
        assert session.message_count == initial_count + 1
        assert session.last_accessed > initial_time

    def test_multiple_increment_message_count(self):
        """여러 번 메시지 카운트 증가 테스트"""
        # given
        session = ChatSession.new("테스트 세션")
        
        # when
        for _ in range(5):
            session.increment_message_count()
        
        # then
        assert session.message_count == 5

    def test_close_session(self):
        """세션 종료 테스트"""
        # given
        session = ChatSession.new("테스트 세션")
        initial_time = session.last_accessed
        
        # when
        session.close()
        
        # then
        assert session.is_active is False
        assert session.last_accessed > initial_time

    def test_close_already_closed_session(self):
        """이미 종료된 세션 재종료 테스트"""
        # given
        session = ChatSession.new("테스트 세션")
        session.close()
        first_close_time = session.last_accessed
        
        # when
        session.close()
        
        # then
        assert session.is_active is False
        assert session.last_accessed >= first_close_time

    def test_post_init_metadata(self):
        """__post_init__ 메타데이터 초기화 테스트"""
        # given & when
        session = ChatSession(
            session_id="test_id",
            title="테스트",
            chatbot_id="bot1",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            metadata=None  # None으로 설정
        )
        
        # then
        assert session.metadata == {}

    def test_post_init_with_existing_metadata(self):
        """기존 메타데이터가 있는 경우 __post_init__ 테스트"""
        # given
        existing_metadata = {"key": "value"}
        
        # when
        session = ChatSession(
            session_id="test_id",
            title="테스트",
            chatbot_id="bot1",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            metadata=existing_metadata
        )
        
        # then
        assert session.metadata == existing_metadata


class TestChatMessage:
    """ChatMessage 도메인 객체 테스트"""

    def test_chat_message_creation(self):
        """ChatMessage 생성 테스트"""
        # given
        content = "안녕하세요"
        role = "user"
        timestamp = datetime.now()
        session_id = "test_session_id"
        
        # when
        message = ChatMessage(
            content=content,
            role=role,
            timestamp=timestamp,
            session_id=session_id
        )
        
        # then
        assert message.content == content
        assert message.role == role
        assert message.timestamp == timestamp
        assert message.session_id == session_id
        assert message.metadata == {}

    def test_chat_message_post_init_metadata(self):
        """ChatMessage __post_init__ 메타데이터 초기화 테스트"""
        # given & when
        message = ChatMessage(
            content="테스트",
            role="user",
            timestamp=datetime.now(),
            session_id="test_session",
            metadata=None
        )
        
        # then
        assert message.metadata == {}

    def test_chat_message_with_existing_metadata(self):
        """기존 메타데이터가 있는 ChatMessage 테스트"""
        # given
        existing_metadata = {"source": "api", "priority": "high"}
        
        # when
        message = ChatMessage(
            content="테스트",
            role="user",
            timestamp=datetime.now(),
            session_id="test_session",
            metadata=existing_metadata
        )
        
        # then
        assert message.metadata == existing_metadata

    def test_chat_message_roles(self):
        """다양한 역할의 ChatMessage 테스트"""
        # given
        roles = ["user", "assistant", "system"]
        timestamp = datetime.now()
        session_id = "test_session"
        
        for role in roles:
            # when
            message = ChatMessage(
                content=f"{role} 메시지",
                role=role,
                timestamp=timestamp,
                session_id=session_id
            )
            
            # then
            assert message.role == role

    def test_chat_message_empty_content(self):
        """빈 내용의 ChatMessage 테스트"""
        # when
        message = ChatMessage(
            content="",
            role="assistant",
            timestamp=datetime.now(),
            session_id="test_session"
        )
        
        # then
        assert message.content == ""

    def test_chat_message_long_content(self):
        """긴 내용의 ChatMessage 테스트"""
        # given
        long_content = "A" * 10000
        
        # when
        message = ChatMessage(
            content=long_content,
            role="assistant",
            timestamp=datetime.now(),
            session_id="test_session"
        )
        
        # then
        assert message.content == long_content
        assert len(message.content) == 10000


class TestChatSessionAndMessageIntegration:
    """ChatSession과 ChatMessage 통합 테스트"""

    def test_session_and_message_relationship(self):
        """세션과 메시지 관계 테스트"""
        # given
        session = ChatSession.new("통합 테스트 세션")
        
        # when
        message1 = ChatMessage(
            content="첫 번째 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        
        message2 = ChatMessage(
            content="두 번째 메시지",
            role="assistant",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        
        # then
        assert message1.session_id == session.session_id
        assert message2.session_id == session.session_id

    def test_conversation_timeline(self):
        """대화 타임라인 테스트"""
        # given
        session = ChatSession.new("타임라인 테스트")
        base_time = datetime.now()
        
        # when
        messages = []
        for i in range(3):
            message = ChatMessage(
                content=f"메시지 {i+1}",
                role="user" if i % 2 == 0 else "assistant",
                timestamp=base_time + timedelta(seconds=i),
                session_id=session.session_id
            )
            messages.append(message)
        
        # then
        # 시간순으로 정렬되어 있는지 확인
        for i in range(1, len(messages)):
            assert messages[i].timestamp >= messages[i-1].timestamp

    def test_metadata_usage(self):
        """메타데이터 활용 테스트"""
        # given
        session = ChatSession.new("메타데이터 테스트")
        session.metadata["user_id"] = "user123"
        session.metadata["language"] = "ko"
        
        message = ChatMessage(
            content="메타데이터 테스트 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        message.metadata["ip_address"] = "192.168.1.1"
        message.metadata["device"] = "mobile"
        
        # then
        assert session.metadata["user_id"] == "user123"
        assert session.metadata["language"] == "ko"
        assert message.metadata["ip_address"] == "192.168.1.1"
        assert message.metadata["device"] == "mobile"

    def test_session_lifecycle_with_messages(self):
        """메시지와 함께하는 세션 생명주기 테스트"""
        # given
        session = ChatSession.new("생명주기 테스트")
        
        # when: 활성 상태에서 메시지 추가
        assert session.is_active is True
        
        message1 = ChatMessage(
            content="활성 상태 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        session.increment_message_count()
        
        # when: 세션 종료
        session.close()
        
        message2 = ChatMessage(
            content="종료 후 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=session.session_id
        )
        
        # then
        assert session.is_active is False
        assert session.message_count == 1
        
        # 종료된 세션에도 메시지는 연결될 수 있음
        assert message1.session_id == session.session_id
        assert message2.session_id == session.session_id
