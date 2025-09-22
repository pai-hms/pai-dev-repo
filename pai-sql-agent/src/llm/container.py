"""
LLM 모듈용 의존성 주입 컨테이너 - dependency-injector 사용
"""
import logging
import httpx
from dependency_injector import containers, providers
from src.agent.settings import get_settings
from .provider import ChatModelProvider
from .service import LLMService

logger = logging.getLogger(__name__)


class LLMContainer(containers.DeclarativeContainer):
    """LLM 모듈용 의존성 주입 컨테이너"""
    
    # Configuration
    config = providers.Configuration()
    
    # Settings
    settings = providers.Singleton(get_settings)
    
    # HTTP Client
    http_client = providers.Singleton(
        httpx.AsyncClient,
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        ),
        timeout=httpx.Timeout(30.0)
    )
    
    # Chat Model Provider
    chat_model_provider = providers.Singleton(
        ChatModelProvider,
        settings=settings,
        http_client=http_client
    )
    
    # LLM Service
    llm_service = providers.Factory(
        LLMService,
        chat_model_provider=chat_model_provider,
        settings=settings
    )


# 전역 컨테이너 인스턴스
_llm_container = None


def get_llm_container() -> LLMContainer:
    """LLM 컨테이너 싱글톤 인스턴스 반환"""
    global _llm_container
    
    if _llm_container is None:
        _llm_container = LLMContainer()
        logger.info("LLM DI 컨테이너 생성 완료")
    
    return _llm_container


async def close_llm_container():
    """LLM 컨테이너 정리"""
    global _llm_container
    
    if _llm_container is not None:
        # HTTP 클라이언트 정리
        try:
            http_client = _llm_container.http_client()
            if hasattr(http_client, 'aclose'):
                await http_client.aclose()
        except Exception as e:
            logger.error(f"HTTP 클라이언트 정리 실패: {e}")
        
        _llm_container = None
        logger.info("LLM DI 컨테이너 정리 완료")