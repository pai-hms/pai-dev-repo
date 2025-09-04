# rag-server/src/chat_session/container.py
from dependency_injector import containers, providers
from .repository import ChatSessionRepository
from .service import ChatSessionService

class ChatSessionContainer(containers.DeclarativeContainer):
    """Chat Session 모듈 DI Container"""
    
    # === Repository 계층 (외부 노출 금지) ===
    repository = providers.Singleton(ChatSessionRepository)
    
    # === Service 계층 (유일한 외부 인터페이스) ===
    service = providers.Singleton(
        ChatSessionService,
        repository=repository
    )

def create_chat_session_container() -> ChatSessionContainer:
    """Chat Session Container 생성"""
    return ChatSessionContainer()