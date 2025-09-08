# rag-server/webapp/container.py
import logging
from dependency_injector import containers, providers

# 모듈별 Container import (Stock 제거)
from src.agent.container import create_agent_container
from src.llm.container import create_llm_container
from src.chatbot.container import create_chatbot_container
from src.chat_session.container import create_chat_session_container

logger = logging.getLogger(__name__)

class StockChatbotContainer(containers.DeclarativeContainer):
    """주식 챗봇 애플리케이션 컨테이너"""

    wiring_config = containers.WiringConfiguration(packages=["webapp"])
    
    # === Module Containers ===
    llm_container = providers.DependenciesContainer()
    agent_container = providers.DependenciesContainer()
    chat_session_container = providers.DependenciesContainer()
    chatbot_container = providers.DependenciesContainer()
    
    # === Service Layer ===
    llm_service = providers.Singleton(
        lambda container: container.service(),
        container=llm_container
    )
    
    agent_executor = providers.Singleton(
        lambda container: container.executor(),
        container=agent_container
    )
    
    chat_session_service = providers.Singleton(
        lambda container: container.service(),
        container=chat_session_container
    )
    
    chatbot_service = providers.Singleton(
        lambda container: container.service(),
        container=chatbot_container
    )

def create_container() -> StockChatbotContainer:
    """컨테이너 생성 및 초기화"""
    container = StockChatbotContainer()
    
    # 모듈별 Container 생성
    llm_container = create_llm_container()
    agent_container = create_agent_container(llm_container)  # LLM Container 전달
    chat_session_container = create_chat_session_container()
    chatbot_container = create_chatbot_container()
    
    # 핵심: Chat Session Service를 Chatbot에 주입
    chatbot_container.chat_session_service.override(chat_session_container.service)
    chatbot_container.agent_executor.override(agent_container.executor)
    
    # Container 등록
    container.llm_container.override(llm_container)
    container.agent_container.override(agent_container)
    container.chat_session_container.override(chat_session_container)
    container.chatbot_container.override(chatbot_container)
    
    return container