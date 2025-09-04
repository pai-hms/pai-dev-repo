# rag-server/webapp/dependency.py
from fastapi import Depends
from src.chatbot.services import chatbot_service

def get_chatbot_service():
    """챗봇 서비스 의존성"""
    return chatbot_service

# 향후 확장을 위한 기본 구조
def get_llm_service():
    """LLM 서비스 의존성 (향후 구현)"""
    pass

def get_agent_service():
    """에이전트 서비스 의존성 (향후 구현)"""
    pass