"""
애플리케이션 전체 의존성 주입 컨테이너
"""
import logging
from dependency_injector import containers, providers
from src.agent.container import AgentContainer
from src.llm.container import LLMContainer

logger = logging.getLogger(__name__)


class ApplicationContainer(containers.DeclarativeContainer):
    """애플리케이션 전체 의존성 주입 컨테이너"""
    
    # Configuration
    config = providers.Configuration()
    
    # Sub-containers
    llm = providers.Container(LLMContainer)
    
    # Agent container with LLM dependency
    agent = providers.Container(
        AgentContainer,
        llm=llm  # LLM 컨테이너를 Agent 컨테이너에 주입
    )


# 전역 애플리케이션 컨테이너
_app_container = None


def get_app_container() -> ApplicationContainer:
    """애플리케이션 컨테이너 싱글톤 인스턴스 반환"""
    global _app_container
    
    if _app_container is None:
        _app_container = ApplicationContainer()
        logger.info("Application DI 컨테이너 생성 완료")
    
    return _app_container


async def close_app_container():
    """애플리케이션 컨테이너 정리"""
    global _app_container
    
    if _app_container is not None:
        try:
            # 모든 리소스 정리
            await _app_container.shutdown_resources()
        except Exception as e:
            logger.error(f"Application 컨테이너 정리 실패: {e}")
        
        _app_container = None
        logger.info("Application DI 컨테이너 정리 완료")
