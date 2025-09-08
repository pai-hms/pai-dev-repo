# rag-server/src/chatbot/container.py
from dependency_injector import containers, providers
from .repository import ChatbotConfigRepository
from .service import ChatbotService

class ChatbotContainer(containers.DeclarativeContainer):
    """Chatbot 모듈 DI Container"""
    
    # === 외부 의존성 ===
    chat_session_service = providers.Dependency()  # Chat Session Service 주입
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
    return ChatbotContainer()