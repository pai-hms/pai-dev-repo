# rag-server/src/chatbot/container.py
from dependency_injector import containers, providers
from .repository import ChatbotConfigRepository  # 올바른 클래스명
from .service import ChatbotService
from src.chat_session.service import ChatSessionService

class ChatbotContainer(containers.DeclarativeContainer):
    """Chatbot 모듈 DI Container - 수정됨"""
    
    # === 외부 의존성 ===
    chat_session_service = providers.Dependency()
    agent_executor = providers.Dependency()
    
    # === Repository 계층 ===
    config_repository = providers.Singleton(ChatbotConfigRepository)
    
    # === Service 계층 ===
    service = providers.Singleton(
        ChatbotService,
        chat_session_service=chat_session_service,
        config_repository=config_repository,
        agent_executor=agent_executor
    )

def create_chatbot_container() -> ChatbotContainer:
    """Chatbot Container 생성"""
    return ChatbotContainer()