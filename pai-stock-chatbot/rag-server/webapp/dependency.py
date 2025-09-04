# rag-server/webapp/dependency.py
from typing import Annotated, Optional
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.chatbot.services import ChatbotService  # 이제 올바른 클래스명
from src.llm.service import LLMService
from src.stock.services import StockService
from src.exceptions import InvalidTokenException, PermissionDeniedException
from webapp.container import StockChatbotContainer

security_scheme = HTTPBearer(auto_error=False)

# === 서비스 의존성들 ===
@inject
def get_chatbot_service(
    service = Depends(Provide[StockChatbotContainer.chatbot_service])
):
    """챗봇 서비스 의존성"""
    return service

@inject
def get_llm_service(
    service = Depends(Provide[StockChatbotContainer.llm_service])
):
    """LLM 서비스 의존성"""
    return service

@inject
def get_stock_service(
    service = Depends(Provide[StockChatbotContainer.stock_service])
):
    """주식 서비스 의존성"""
    return service

# === 인증 관련 의존성들 ===
async def api_key_dependency(
    stock_api_key: Annotated[
        Optional[str], 
        Header(alias="Stock-API-Key", description="주식 API 키")
    ] = None,
) -> Optional[dict]:
    """API 키 인증 (향후 구현)"""
    if stock_api_key:
        # TODO: 실제 API 키 검증 로직 구현
        return {"api_key": stock_api_key, "verified": True}
    return None

async def user_auth_dependency(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], 
        Depends(security_scheme)
    ] = None,
) -> Optional[dict]:
    """사용자 인증 (향후 구현)"""
    if credentials:
        # TODO: 실제 토큰 검증 로직 구현
        token = credentials.credentials
        
        # 간단한 토큰 형식 검증
        if len(token) < 10:
            raise InvalidTokenException("유효하지 않은 토큰입니다")
        
        return {
            "token": token,
            "user_id": "user_123",  # 임시
            "verified": True
        }
    return None

def admin_user_dependency(
    user_auth: Optional[dict] = Depends(user_auth_dependency),
) -> dict:
    """관리자 권한 확인 (향후 구현)"""
    if not user_auth:
        raise PermissionDeniedException("인증이 필요합니다")
    
    # TODO: 실제 관리자 권한 확인 로직
    if user_auth.get("user_id") != "admin_user":
        raise PermissionDeniedException("관리자 권한이 필요합니다")
    
    return user_auth

# === 설정 관련 의존성들 ===
def get_app_settings() -> dict:
    """애플리케이션 설정 (향후 구현)"""
    return {
        "debug": True,
        "max_message_length": 1000,
        "default_stock_currency": "USD",
        "rate_limit": 100
    }

# === 헬스체크 의존성 ===
async def health_check_dependency() -> dict:
    """헬스체크 정보"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "chatbot": "up",
            "llm": "up", 
            "stock": "up"
        }
    }