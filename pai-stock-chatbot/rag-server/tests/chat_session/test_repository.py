# tests/chat_session/test_repository.py
import pytest
from datetime import datetime

from src.chat_session.repository import ChatSessionRepository
from src.chat_session.domains import ChatSession, ChatMessage


class TestChatSessionRepository:
    """ChatSessionRepository 테스트"""

    @pytest.fixture
    def repository(self):
        """Repository 인스턴스"""
        return ChatSessionRepository()

    @pytest.fixture
    def sample_session(self):
        """샘플 세션"""
        return ChatSession.new(title="테스트 세션", chatbot_id="test_bot")

    @pytest.fixture
    def sample_message(self, sample_session):
        """샘플 메시지"""
        return ChatMessage(
            content="테스트 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=sample_session.session_id
        )

    def test_save_and_find_session(self, repository, sample_session):
        """세션 저장 및 조회 테스트"""
        # when
        repository.save_session(sample_session)
        
        # then
        found_session = repository.find_session_by_id(sample_session.session_id)
        assert found_session is not None
        assert found_session.session_id == sample_session.session_id
        assert found_session.title == sample_session.title
        assert found_session.chatbot_id == sample_session.chatbot_id

    def test_find_session_not_found(self, repository):
        """존재하지 않는 세션 조회 테스트"""
        # when
        result = repository.find_session_by_id("non_existent_id")
        
        # then
        assert result is None

    def test_delete_session(self, repository, sample_session):
        """세션 삭제 테스트"""
        # given
        repository.save_session(sample_session)
        
        # when
        result = repository.delete_session(sample_session.session_id)
        
        # then
        assert result is True
        found_session = repository.find_session_by_id(sample_session.session_id)
        assert found_session is None

    def test_delete_non_existent_session(self, repository):
        """존재하지 않는 세션 삭제 테스트"""
        # when
        result = repository.delete_session("non_existent_id")
        
        # then
        assert result is False

    def test_find_all_sessions(self, repository):
        """모든 세션 조회 테스트"""
        # given
        session1 = ChatSession.new("세션1", "bot1")
        session2 = ChatSession.new("세션2", "bot2")
        repository.save_session(session1)
        repository.save_session(session2)
        
        # when
        all_sessions = repository.find_all_sessions()
        
        # then
        assert len(all_sessions) == 2
        assert session1.session_id in all_sessions
        assert session2.session_id in all_sessions

    def test_find_active_sessions(self, repository):
        """활성 세션만 조회 테스트"""
        # given
        active_session = ChatSession.new("활성 세션", "bot1")
        inactive_session = ChatSession.new("비활성 세션", "bot2")
        inactive_session.close()  # 세션 종료
        
        repository.save_session(active_session)
        repository.save_session(inactive_session)
        
        # when
        active_sessions = repository.find_active_sessions()
        
        # then
        assert len(active_sessions) == 1
        assert active_session.session_id in active_sessions
        assert inactive_session.session_id not in active_sessions

    def test_save_message(self, repository, sample_session, sample_message):
        """메시지 저장 테스트"""
        # given
        repository.save_session(sample_session)
        
        # when
        repository.save_message(sample_message)
        
        # then
        messages = repository.find_messages_by_session(sample_session.session_id)
        assert len(messages) == 1
        assert messages[0].content == sample_message.content
        assert messages[0].role == sample_message.role

    def test_save_multiple_messages(self, repository, sample_session):
        """여러 메시지 저장 테스트"""
        # given
        repository.save_session(sample_session)
        
        messages_data = [
            ("첫번째 메시지", "user"),
            ("AI 응답", "assistant"),
            ("두번째 메시지", "user")
        ]
        
        # when
        for content, role in messages_data:
            message = ChatMessage(
                content=content,
                role=role,
                timestamp=datetime.now(),
                session_id=sample_session.session_id
            )
            repository.save_message(message)
        
        # then
        messages = repository.find_messages_by_session(sample_session.session_id)
        assert len(messages) == 3
        
        for i, (expected_content, expected_role) in enumerate(messages_data):
            assert messages[i].content == expected_content
            assert messages[i].role == expected_role

    def test_message_count_increment(self, repository, sample_session, sample_message):
        """메시지 저장 시 카운트 증가 테스트"""
        # given
        repository.save_session(sample_session)
        initial_count = sample_session.message_count
        
        # when
        repository.save_message(sample_message)
        
        # then
        updated_session = repository.find_session_by_id(sample_session.session_id)
        assert updated_session.message_count == initial_count + 1

    def test_get_message_count(self, repository, sample_session):
        """메시지 개수 조회 테스트"""
        # given
        repository.save_session(sample_session)
        
        # 3개 메시지 저장
        for i in range(3):
            message = ChatMessage(
                content=f"메시지 {i+1}",
                role="user",
                timestamp=datetime.now(),
                session_id=sample_session.session_id
            )
            repository.save_message(message)
        
        # when
        count = repository.get_message_count(sample_session.session_id)
        
        # then
        assert count == 3

    def test_get_message_count_empty(self, repository):
        """빈 세션의 메시지 개수 조회 테스트"""
        # when
        count = repository.get_message_count("non_existent_session")
        
        # then
        assert count == 0

    def test_find_messages_by_session_empty(self, repository):
        """빈 세션의 메시지 조회 테스트"""
        # when
        messages = repository.find_messages_by_session("non_existent_session")
        
        # then
        assert messages == []

    def test_session_deletion_removes_messages(self, repository, sample_session):
        """세션 삭제 시 관련 메시지도 삭제되는지 테스트"""
        # given
        repository.save_session(sample_session)
        
        # 메시지 추가
        message = ChatMessage(
            content="테스트 메시지",
            role="user",
            timestamp=datetime.now(),
            session_id=sample_session.session_id
        )
        repository.save_message(message)
        
        # when
        repository.delete_session(sample_session.session_id)
        
        # then
        messages = repository.find_messages_by_session(sample_session.session_id)
        assert messages == []
        assert repository.get_message_count(sample_session.session_id) == 0

    def test_repository_isolation(self, repository):
        """Repository 인스턴스 간 격리 테스트"""
        # given
        another_repository = ChatSessionRepository()
        session = ChatSession.new("테스트", "bot1")
        
        # when
        repository.save_session(session)
        
        # then
        assert repository.find_session_by_id(session.session_id) is not None
        assert another_repository.find_session_by_id(session.session_id) is None

    def test_immutability_protection(self, repository, sample_session):
        """불변성 보호 테스트"""
        # given
        repository.save_session(sample_session)
        
        # when
        all_sessions = repository.find_all_sessions()
        messages = repository.find_messages_by_session(sample_session.session_id)
        
        # then: 반환된 객체들이 복사본인지 확인
        # (실제 구현에 따라 다를 수 있음)
        assert isinstance(all_sessions, dict)
        assert isinstance(messages, list)
        
        # 원본 데이터 수정이 repository에 영향을 주지 않는지 확인
        original_count = len(all_sessions)
        all_sessions.clear()  # 반환된 dict 수정
        
        # Repository는 영향받지 않아야 함
        assert len(repository.find_all_sessions()) == original_count


class TestChatSessionRepositoryPerformance:
    """ChatSessionRepository 성능 테스트"""

    def test_large_number_of_sessions(self):
        """대량 세션 처리 성능 테스트"""
        # given
        repository = ChatSessionRepository()
        num_sessions = 1000
        
        # when: 대량 세션 생성
        sessions = []
        for i in range(num_sessions):
            session = ChatSession.new(f"세션 {i}", f"bot_{i % 10}")
            repository.save_session(session)
            sessions.append(session)
        
        # then: 조회 성능 확인
        all_sessions = repository.find_all_sessions()
        assert len(all_sessions) == num_sessions
        
        # 개별 조회 성능 확인
        for session in sessions[:10]:  # 첫 10개만 테스트
            found = repository.find_session_by_id(session.session_id)
            assert found is not None

    def test_large_number_of_messages(self):
        """대량 메시지 처리 성능 테스트"""
        # given
        repository = ChatSessionRepository()
        session = ChatSession.new("대량 메시지 테스트", "bot1")
        repository.save_session(session)
        
        num_messages = 1000
        
        # when: 대량 메시지 저장
        for i in range(num_messages):
            message = ChatMessage(
                content=f"메시지 {i}",
                role="user" if i % 2 == 0 else "assistant",
                timestamp=datetime.now(),
                session_id=session.session_id
            )
            repository.save_message(message)
        
        # then: 조회 성능 확인
        messages = repository.find_messages_by_session(session.session_id)
        assert len(messages) == num_messages
        
        count = repository.get_message_count(session.session_id)
        assert count == num_messages
