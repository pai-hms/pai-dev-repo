"""
SQL Agent DI Container - dependency-injector 사용
한국 통계청 데이터 분석을 위한 SQL Agent 서비스들을 관리
"""
import logging
from dependency_injector import containers, providers

from src.config.settings import get_settings
from src.agent.settings import get_agent_settings

logger = logging.getLogger(__name__)


class SQLAgentContainer(containers.DeclarativeContainer):
    """SQL Agent 전용 DI 컨테이너"""
    
    # 기본 설정들
    config = providers.Configuration()
    settings = providers.Resource(get_settings)
    agent_settings = providers.Resource(get_agent_settings)


# 전역 컨테이너 인스턴스
container = SQLAgentContainer()


async def get_container() -> SQLAgentContainer:
    """컨테이너 인스턴스 반환"""
    return container


async def get_service(service_name: str):
    """서비스 가져오기"""
    return getattr(container, service_name)()

