# tests/conftest.py
import pytest
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

# 현재 프로젝트 모듈들
from src.chat_session.repository import ChatSessionRepository
from src.chat_session.service import ChatSessionService
from src.chat_session.domains import ChatSession, ChatMessage

from src.chatbot.repository import ChatbotConfigRepository
from src.chatbot.service import ChatbotService
from src.chatbot.domains import ChatbotConfig

from src.exceptions import InvalidRequestException, SessionNotFoundException


@pytest.fixture(scope="session")
def initialize_test_logger():
    """테스트 로거 초기화"""
    logger = logging.getLogger()
    logger.setLevel("INFO")
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="[%(levelname)5s][%(filename)s:%(lineno)s] %(message)s",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@pytest.fixture(scope="session")
def event_loop(initialize_test_logger):
    """테스트용 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_collection_modifyitems(items):
    """비동기 테스트에 session 스코프 마커 추가"""
    from pytest_asyncio import is_async_test

    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


# === Repository Fixtures ===
@pytest.fixture
def chat_session_repository():
    """ChatSession Repository"""
    return ChatSessionRepository()


@pytest.fixture
def chatbot_config_repository():
    """ChatbotConfig Repository"""
    return ChatbotConfigRepository()


# === Mock 객체들 ===
@pytest.fixture
def mock_llm_service():
    """Mock LLM Service"""
    mock = MagicMock()
    
    # Mock methods
    mock.prepare_messages.return_value = [HumanMessage(content="test")]
    mock.get_llm_with_tools.return_value = MagicMock()
    mock.get_llm_with_tools.return_value.invoke.return_value = AIMessage(content="test response")
    
    return mock


@pytest.fixture
def mock_agent_executor():
    """Mock Agent Executor"""
    mock = MagicMock()
    
    async def mock_astream(*args, **kwargs):
        """Mock streaming response"""
        yield {"messages": [AIMessage(content="테스트 응답입니다.")]}
    
    mock.astream = mock_astream
    return mock


# === Service Fixtures ===
@pytest.fixture
def chat_session_service(chat_session_repository):
    """ChatSession Service"""
    return ChatSessionService(repository=chat_session_repository)


@pytest.fixture
def chatbot_service(chat_session_service, chatbot_config_repository, mock_agent_executor):
    """Chatbot Service"""
    return ChatbotService(
        chat_session_service=chat_session_service,
        config_repository=chatbot_config_repository,
        agent_executor=mock_agent_executor
    )


# === Domain Object Fixtures ===
@pytest.fixture
def sample_chatbot_config():
    """샘플 챗봇 설정"""
    return ChatbotConfig.default()


@pytest.fixture
def sample_chat_session():
    """샘플 채팅 세션"""
    return ChatSession.new(title="테스트 세션", chatbot_id="default")


@pytest.fixture
def sample_chat_message(sample_chat_session):
    """샘플 채팅 메시지"""
    return ChatMessage(
        content="안녕하세요",
        role="user",
        timestamp=datetime.now(),
        session_id=sample_chat_session.session_id
    )


# === 테스트 데이터 ===
@pytest.fixture
def sample_query():
    """샘플 질의"""
    return "AAPL 주가 알려줘"


@pytest.fixture
def test_session_id():
    """테스트용 세션 ID"""
    return "test_session_123"


@pytest.fixture
def test_message():
    """테스트용 메시지"""
    return "100 곱하기 1.5는?"


# === 초기화 Fixtures ===
@pytest.fixture
async def initialize_test_data(
    sample_chatbot_config,
    chatbot_config_repository
):
    """테스트 데이터 초기화"""
    # 기본 챗봇 설정 저장
    chatbot_config_repository.save_config("default", sample_chatbot_config)
    yield
    # 정리는 자동으로 됨 (메모리 기반)


@pytest.fixture(autouse=True)
def test_info(request):
    """테스트 정보 출력"""
    logger = logging.getLogger()
    logger.info(f"테스트 시작: {request.node.name}")
    yield
    logger.info(f"테스트 완료: {request.node.name}")