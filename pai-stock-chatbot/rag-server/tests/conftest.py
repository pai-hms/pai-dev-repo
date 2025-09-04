# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator
from datetime import datetime

from src.chat_session.repository import ChatSessionRepository
from src.chat_session.service import ChatSessionService
from src.chat_session.domains import ChatSession, ChatMessage

from src.chatbot.repository import ChatbotConfigRepository
from src.chatbot.service import ChatbotService
from src.chatbot.domains import ChatbotConfig

from src.stock.repository import StockRepository
from src.stock.services import StockService

from src.llm.service import LLMService
from src.agent.service import AgentService

from langchain_core.messages import HumanMessage, AIMessage


# === Mock 객체들 ===
@pytest.fixture
def mock_agent_executor():
    """Mock Agent Executor"""
    mock = MagicMock()
    
    async def mock_astream(*args, **kwargs):
        """Mock streaming response"""
        yield {"messages": [AIMessage(content="테스트 응답입니다.")]}
    
    mock.astream = mock_astream
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM Service"""
    mock = MagicMock(spec=LLMService)
    mock.get_llm_with_tools = MagicMock(return_value=MagicMock())
    mock.prepare_messages = MagicMock(return_value=[])
    return mock


# === Repository Fixtures ===
@pytest.fixture
def chat_session_repository():
    """ChatSession Repository"""
    return ChatSessionRepository()


@pytest.fixture
def chatbot_config_repository():
    """ChatbotConfig Repository"""
    return ChatbotConfigRepository()


@pytest.fixture
def stock_repository():
    """Stock Repository"""
    return StockRepository()


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


@pytest.fixture
def stock_service(stock_repository):
    """Stock Service"""
    return StockService(repository=stock_repository)


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


@pytest.fixture
def sample_query():
    """샘플 질의"""
    return "AAPL 주가 알려줘"


# === 테스트 데이터 ===
@pytest.fixture
def test_session_id():
    """테스트용 세션 ID"""
    return "test_session_123"


@pytest.fixture
def test_message():
    """테스트용 메시지"""
    return "100 곱하기 1.5는?"
