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


# ✅ 추가: 개별 서비스 팩토리 함수들
async def get_database_service():
    """데이터베이스 서비스 반환"""
    from src.database.service import get_database_service
    return await get_database_service()


async def get_llm_service():
    """LLM 서비스 반환"""
    from src.llm.service import get_llm_service
    return await get_llm_service()


async def get_session_service():
    """세션 서비스 반환"""
    from src.session.service import get_session_service
    return await get_session_service()

