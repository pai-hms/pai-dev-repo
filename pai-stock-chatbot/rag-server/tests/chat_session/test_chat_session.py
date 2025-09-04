# tests/chat_session/test_service.py
import pytest
from datetime import datetime
from unittest.mock import patch

from src.chat_session.service import ChatSessionService
from src.chat_session.domains import ChatSession, ChatMessage
from src.exceptions import SessionNotFoundException

# asyncio_mode = auto 설정으로 @pytest.mark.asyncio 불필요
# 클래스 레벨에서 한 번만 설정
@pytest.mark.asyncio
class TestChatSessionService:
    """ChatSessionService 테스트 - asyncio_mode=auto 적용"""

    async def test_start_new_session(self, chat_session_service: ChatSessionService):
        """새 세션 시작 테스트"""
        # given
        title = "테스트 세션"
        chatbot_id = "test_bot"
        
        # when
        session = await chat_session_service.start_new_session(title, chatbot_id)
        
        # then
        assert session.title == title
        assert session.chatbot_id == chatbot_id
        assert session.session_id is not None
        assert session.is_active is True
        assert session.message_count == 0

    async def test_get_session_success(self, chat_session_service: ChatSessionService):
        """세션 조회 성공 테스트"""
        # given
        session = await chat_session_service.start_new_session("테스트", "bot1")
        
        # when
        retrieved_session = await chat_session_service.get_session(session.session_id)
        
        # then
        assert retrieved_session.session_id == session.session_id
        assert retrieved_session.title == session.title

    async def test_get_session_not_found(self, chat_session_service: ChatSessionService):
        """세션 조회 실패 테스트"""
        # given
        non_existent_id = "non_existent_session"
        
        # when & then
        with pytest.raises(SessionNotFoundException) as exc_info:
            await chat_session_service.get_session(non_existent_id)
        
        assert "not found" in str(exc_info.value)

    async def test_close_session(self, chat_session_service: ChatSessionService):
        """세션 종료 테스트"""
        # given
        session = await chat_session_service.start_new_session("테스트", "bot1")
        assert session.is_active is True
        
        # when
        result = await chat_session_service.close_session(session.session_id)
        
        # then
        assert result is True
        updated_session = await chat_session_service.get_session(session.session_id)
        assert updated_session.is_active is False

    async def test_get_active_sessions(self, chat_session_service: ChatSessionService):
        """활성 세션 목록 조회 테스트"""
        # given
        session1 = await chat_session_service.start_new_session("세션1", "bot1")
        session2 = await chat_session_service.start_new_session("세션2", "bot1")
        await chat_session_service.close_session(session2.session_id)  # 하나는 종료
        
        # when
        active_sessions = await chat_session_service.get_active_sessions()
        
        # then
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == session1.session_id
        assert active_sessions[0].is_active is True

    async def test_save_message(self, chat_session_service: ChatSessionService):
        """메시지 저장 테스트"""
        # given
        session = await chat_session_service.start_new_session("테스트", "bot1")
        content = "안녕하세요"
        role = "user"
        
        # when
        message = await chat_session_service.save_message(session.session_id, content, role)
        
        # then
        assert message.content == content
        assert message.role == role
        assert message.session_id == session.session_id
        assert message.timestamp is not None
        
        # 세션의 메시지 카운트가 증가했는지 확인
        updated_session = await chat_session_service.get_session(session.session_id)
        assert updated_session.message_count == 1

    async def test_save_multiple_messages(self, chat_session_service: ChatSessionService):
        """여러 메시지 저장 테스트"""
        # given
        session = await chat_session_service.start_new_session("테스트", "bot1")
        
        # when
        await chat_session_service.save_message(session.session_id, "첫번째 메시지", "user")
        await chat_session_service.save_message(session.session_id, "두번째 메시지", "assistant")
        await chat_session_service.save_message(session.session_id, "세번째 메시지", "user")
        
        # then
        messages = await chat_session_service.get_messages(session.session_id)
        assert len(messages) == 3
        assert messages[0].content == "첫번째 메시지"
        assert messages[1].content == "두번째 메시지"
        assert messages[2].content == "세번째 메시지"
        
        # 세션의 메시지 카운트 확인
        updated_session = await chat_session_service.get_session(session.session_id)
        assert updated_session.message_count == 3

    async def test_get_messages_from_non_existent_session(self, chat_session_service: ChatSessionService):
        """존재하지 않는 세션의 메시지 조회 테스트"""
        # given
        non_existent_id = "non_existent_session"
        
        # when & then
        with pytest.raises(SessionNotFoundException):
            await chat_session_service.get_messages(non_existent_id)

    async def test_save_message_to_non_existent_session(self, chat_session_service: ChatSessionService):
        """존재하지 않는 세션에 메시지 저장 테스트"""
        # given
        non_existent_id = "non_existent_session"
        
        # when & then
        with pytest.raises(SessionNotFoundException):
            await chat_session_service.save_message(non_existent_id, "메시지", "user")


@pytest.mark.asyncio
class TestChatSessionIntegration:
    """ChatSession 통합 테스트"""

    async def test_complete_chat_flow(self, chat_session_service: ChatSessionService):
        """완전한 채팅 플로우 테스트"""
        # given: 새 세션 시작
        session = await chat_session_service.start_new_session("통합 테스트", "integration_bot")
        
        # when: 사용자 메시지 저장
        user_message = await chat_session_service.save_message(
            session.session_id, "AAPL 주가 알려줘", "user"
        )
        
        # when: AI 응답 저장
        ai_message = await chat_session_service.save_message(
            session.session_id, "AAPL 현재 가격은 $150입니다.", "assistant"
        )
        
        # then: 메시지 순서 확인
        messages = await chat_session_service.get_messages(session.session_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        
        # then: 세션 상태 확인
        final_session = await chat_session_service.get_session(session.session_id)
        assert final_session.message_count == 2
        assert final_session.is_active is True
        
        # when: 세션 종료
        await chat_session_service.close_session(session.session_id)
        
        # then: 종료 상태 확인
        closed_session = await chat_session_service.get_session(session.session_id)
        assert closed_session.is_active is False
