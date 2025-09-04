# tests/chatbot/test_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from src.chatbot.service import ChatbotService
from src.chatbot.domains import ChatbotConfig
from src.exceptions import InvalidRequestException, ChatbotServiceException, SessionNotFoundException

# asyncio_mode = auto 설정으로 클래스 레벨에서 한 번만 데코레이터 적용
@pytest.mark.asyncio
class TestChatbotService:
    """ChatbotService 테스트"""

    async def test_stream_response_with_new_session(self, chatbot_service: ChatbotService):
        """새 세션으로 스트리밍 응답 테스트"""
        # given
        session_id = "new_test_session"
        message = "안녕하세요"
        
        # when
        responses = []
        async for response in chatbot_service.stream_response(session_id, message):
            responses.append(response)
        
        # then
        assert len(responses) > 0
        assert any("테스트 응답" in response for response in responses)

    async def test_stream_response_with_existing_session(self, chatbot_service: ChatbotService):
        """기존 세션으로 스트리밍 응답 테스트"""
        # given
        session_id = "existing_session"
        # 먼저 세션 생성
        await chatbot_service.start_new_chat("기존 세션", "default")
        chatbot_service._session_service._repository.save_session(
            chatbot_service._session_service._repository._sessions[list(chatbot_service._session_service._repository._sessions.keys())[0]]
        )
        
        # session_id 업데이트
        sessions = chatbot_service._session_service._repository._sessions
        if sessions:
            session = list(sessions.values())[0]
            session.session_id = session_id
            chatbot_service._session_service._repository.save_session(session)
        
        message = "두 번째 메시지"
        
        # when
        responses = []
        async for response in chatbot_service.stream_response(session_id, message):
            responses.append(response)
        
        # then
        assert len(responses) > 0

    async def test_stream_response_input_validation(self, chatbot_service: ChatbotService):
        """입력 검증 테스트"""
        # 빈 세션 ID 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            async for _ in chatbot_service.stream_response("", "메시지"):
                pass
        assert "세션 ID가 비어있습니다" in str(exc_info.value)
        
        # 빈 메시지 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            async for _ in chatbot_service.stream_response("session_id", ""):
                pass
        assert "메시지가 비어있습니다" in str(exc_info.value)
        
        # 너무 긴 메시지 테스트
        long_message = "a" * 1001
        with pytest.raises(InvalidRequestException) as exc_info:
            async for _ in chatbot_service.stream_response("session_id", long_message):
                pass
        assert "1000자를 초과할 수 없습니다" in str(exc_info.value)
        
        # 유효하지 않은 문자 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            async for _ in chatbot_service.stream_response("session_id", "메시지<script>"):
                pass
        assert "허용되지 않는 문자" in str(exc_info.value)

    async def test_start_new_chat(self, chatbot_service: ChatbotService):
        """새 채팅 시작 테스트"""
        # given
        title = "새로운 채팅"
        chatbot_id = "test_bot"
        
        # when
        session_id = await chatbot_service.start_new_chat(title, chatbot_id)
        
        # then
        assert session_id is not None
        session_info = await chatbot_service.get_session_info(session_id)
        assert session_info["title"] == title
        assert session_info["chatbot_id"] == chatbot_id

    async def test_get_session_info(self, chatbot_service: ChatbotService):
        """세션 정보 조회 테스트"""
        # given
        session_id = await chatbot_service.start_new_chat("테스트 세션", "default")
        
        # when
        session_info = await chatbot_service.get_session_info(session_id)
        
        # then
        assert session_info is not None
        assert session_info["session_id"] == session_id
        assert session_info["title"] == "테스트 세션"
        assert session_info["chatbot_id"] == "default"
        assert "created_at" in session_info
        assert "last_accessed" in session_info
        assert "message_count" in session_info
        assert "is_active" in session_info

    async def test_close_session(self, chatbot_service: ChatbotService):
        """세션 종료 테스트"""
        # given
        session_id = await chatbot_service.start_new_chat("테스트 세션", "default")
        
        # when
        result = await chatbot_service.close_session(session_id)
        
        # then
        assert result is True

    async def test_get_all_active_sessions(self, chatbot_service: ChatbotService):
        """모든 활성 세션 조회 테스트"""
        # given
        session1_id = await chatbot_service.start_new_chat("세션 1", "bot1")
        session2_id = await chatbot_service.start_new_chat("세션 2", "bot2")
        await chatbot_service.close_session(session2_id)  # 하나는 종료
        
        # when
        active_sessions = await chatbot_service.get_all_active_sessions()
        
        # then
        assert len(active_sessions) >= 1
        # 활성 세션만 포함되어야 함
        active_session_ids = [session["session_id"] for session in active_sessions]
        assert session1_id in active_session_ids

    async def test_get_chatbot_config(self, chatbot_service: ChatbotService):
        """챗봇 설정 조회 테스트"""
        # given
        chatbot_id = "default"
        
        # when
        config = await chatbot_service.get_chatbot_config(chatbot_id)
        
        # then
        assert isinstance(config, ChatbotConfig)
        assert config.chatbot_id == "default"
        assert config.model_name is not None
        assert config.system_prompt is not None

    async def test_update_chatbot_config(self, chatbot_service: ChatbotService):
        """챗봇 설정 업데이트 테스트"""
        # given
        chatbot_id = "default"
        update_data = {
            "temperature": 0.8,
            "max_tokens": 2000,
            "system_prompt": "새로운 시스템 프롬프트"
        }
        
        # when
        updated_config = await chatbot_service.update_chatbot_config(chatbot_id, update_data)
        
        # then
        assert updated_config.temperature == 0.8
        assert updated_config.max_tokens == 2000
        assert updated_config.system_prompt == "새로운 시스템 프롬프트"

    async def test_config_validation(self, chatbot_service: ChatbotService):
        """설정 관련 검증 테스트"""
        # 빈 chatbot_id 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            await chatbot_service.get_chatbot_config("")
        assert "챗봇 ID가 비어있습니다" in str(exc_info.value)
        
        # 빈 설정 데이터 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            await chatbot_service.update_chatbot_config("default", {})
        assert "설정 데이터가 비어있습니다" in str(exc_info.value)


@pytest.mark.asyncio
class TestChatbotServiceErrorHandling:
    """ChatbotService 에러 처리 테스트"""

    async def test_agent_executor_failure(self, chat_session_service, chatbot_config_repository):
        """Agent Executor 실패 시 처리 테스트"""
        # given: 실패하는 mock agent executor
        failing_agent = MagicMock()
        
        async def failing_astream(*args, **kwargs):
            raise Exception("Agent execution failed")
        
        failing_agent.astream = failing_astream
        
        chatbot_service = ChatbotService(
            chat_session_service=chat_session_service,
            config_repository=chatbot_config_repository,
            agent_executor=failing_agent
        )
        
        # when & then
        with pytest.raises(ChatbotServiceException) as exc_info:
            async for _ in chatbot_service.stream_response("test_session", "메시지"):
                pass
        
        assert "응답 생성 중 오류가 발생했습니다" in str(exc_info.value)

    async def test_content_validation(self, chatbot_service: ChatbotService):
        """컨텐츠 검증 테스트"""
        # given: 매우 긴 응답을 생성하는 mock agent
        long_response = "a" * 5001
        
        # mock agent에서 긴 응답 반환하도록 설정
        chatbot_service._agent_executor.astream = AsyncMock()
        
        async def mock_long_astream(*args, **kwargs):
            yield {"messages": [MagicMock(content=long_response)]}
        
        chatbot_service._agent_executor.astream = mock_long_astream
        
        # when
        responses = []
        async for response in chatbot_service.stream_response("test_session", "메시지"):
            responses.append(response)
        
        # then: 응답이 잘렸는지 확인
        assert len(responses) > 0
        assert len(responses[0]) <= 5000
        assert "일부만 표시됩니다" in responses[0]


@pytest.mark.asyncio
class TestChatbotServiceIntegration:
    """ChatbotService 통합 테스트"""

    async def test_complete_chatbot_flow(self, chatbot_service: ChatbotService):
        """완전한 챗봇 플로우 테스트"""
        # given: 새 세션 시작
        session_id = await chatbot_service.start_new_chat("통합 테스트", "default")
        
        # when: 첫 번째 메시지 전송
        responses1 = []
        async for response in chatbot_service.stream_response(session_id, "안녕하세요"):
            responses1.append(response)
        
        # when: 두 번째 메시지 전송
        responses2 = []
        async for response in chatbot_service.stream_response(session_id, "AAPL 주가 알려줘"):
            responses2.append(response)
        
        # then: 응답 검증
        assert len(responses1) > 0
        assert len(responses2) > 0
        
        # then: 세션 정보 확인
        session_info = await chatbot_service.get_session_info(session_id)
        assert session_info["message_count"] >= 4  # user + assistant messages * 2

    async def test_multiple_sessions_isolation(self, chatbot_service: ChatbotService):
        """여러 세션 간 격리 테스트"""
        # given: 두 개의 세션 생성
        session1_id = await chatbot_service.start_new_chat("세션 1", "default")
        session2_id = await chatbot_service.start_new_chat("세션 2", "default")
        
        # when: 각 세션에 메시지 전송
        async for _ in chatbot_service.stream_response(session1_id, "첫 번째 세션 메시지"):
            pass
        
        async for _ in chatbot_service.stream_response(session2_id, "두 번째 세션 메시지"):
            pass
        
        # then: 세션 정보가 독립적인지 확인
        session1_info = await chatbot_service.get_session_info(session1_id)
        session2_info = await chatbot_service.get_session_info(session2_id)
        
        assert session1_info["session_id"] != session2_info["session_id"]
        assert session1_info["title"] != session2_info["title"]
