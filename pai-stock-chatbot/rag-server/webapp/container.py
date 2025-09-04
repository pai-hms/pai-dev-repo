# rag-server/webapp/container.py
import logging
from dependency_injector import containers, providers

# 현재 프로젝트의 서비스들
from src.chatbot.services import ChatbotService
from src.llm.service import LLMService
from src.stock.services import StockService
from src.chat_session.repository import ChatSessionRepository
from src.chat_session.service import ChatSessionService

logger = logging.getLogger(__name__)

class StockChatbotContainer(containers.DeclarativeContainer):
    """주식 챗봇 애플리케이션 컨테이너"""
    
    wiring_config = containers.WiringConfiguration(packages=["webapp"])
    
    # === Repository 계층 ===
    chat_session_repository = providers.Singleton(
        ChatSessionRepository
    )
    
    # === Service 계층 ===
    llm_service = providers.Singleton(LLMService)
    
    chat_session_service = providers.Singleton(
        ChatSessionService,
        repository=chat_session_repository
    )
    
    chatbot_service = providers.Singleton(
        ChatbotService,
        session_service=chat_session_service
    )
    
    # === 주식 서비스 ===
    stock_service = providers.Factory(StockService)

def preload_dependencies(container: StockChatbotContainer):
    """
    첫 API 응답 속도 향상을 위한 의존성 사전 로딩
    """
    try:
        logger.info("Preloading dependencies...")
        
        # 주요 서비스들 미리 초기화
        container.chat_session_repository()
        container.chat_session_service()
        container.llm_service()
        container.chatbot_service()
        container.stock_service()
        
        logger.info("Preloading dependencies... done")
    except Exception as e:
        logger.error(f"Failed to preload dependencies: {e}")

def create_container() -> StockChatbotContainer:
    """컨테이너 생성 및 초기화"""
    container = StockChatbotContainer()
    
    # 의존성 사전 로딩
    preload_dependencies(container)
    
    return container