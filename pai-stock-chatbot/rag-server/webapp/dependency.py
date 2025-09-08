# rag-server/webapp/dependency.py
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from webapp.container import StockChatbotContainer

# === 핵심 서비스 의존성만 ===
@inject
def get_chatbot_service(
    service = Depends(Provide[StockChatbotContainer.chatbot_service])
):
    """챗봇 서비스 의존성"""
    return service

@inject
def get_chat_session_service(
    service = Depends(Provide[StockChatbotContainer.chat_session_service])
):
    """채팅 세션 서비스 의존성"""
    return service

# === 간단한 설정 ===
def get_app_settings() -> dict:
    """애플리케이션 기본 설정"""
    return {
        "max_message_length": 1000,
        "rate_limit": 100
    }