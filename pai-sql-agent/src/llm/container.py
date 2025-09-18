"""
LLM DI Container - dependency-injector 사용
LLM 관련 서비스들의 의존성 주입을 관리
"""
import logging
from dependency_injector import containers, providers

from .service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class LLMContainer(containers.DeclarativeContainer):
    """LLM 모듈 DI 컨테이너"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # LLM Service Layer
    llm_service = providers.Resource(get_llm_service)


# 전역 컨테이너 인스턴스
container = LLMContainer()


async def get_llm_container() -> LLMContainer:
    """LLM 컨테이너 인스턴스 반환"""
    return container


async def get_llm_service_from_container() -> LLMService:
    """컨테이너에서 LLM 서비스 인스턴스 반환"""
    return await container.llm_service()
