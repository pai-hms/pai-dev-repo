"""
Session DI Container - 단순화된 Repository 중심 구조
Repository가 데이터 제어권을 담당하는 아키텍처
"""
import logging
from dependency_injector import containers, providers

from src.database.connection import get_database_manager
from .repository import SessionRepository

logger = logging.getLogger(__name__)


class SessionContainer(containers.DeclarativeContainer):
    """Session 모듈 DI 컨테이너 - 단순화"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # 데이터베이스 매니저 (외부 의존성)
    database_manager = providers.Resource(get_database_manager)


# 전역 컨테이너 인스턴스
container = SessionContainer()


async def get_session_container() -> SessionContainer:
    """세션 컨테이너 인스턴스 반환"""
    return container


async def get_database_manager_from_session_container():
    """세션 컨테이너에서 데이터베이스 매니저 반환"""
    return container.database_manager()


# ✅ SessionService는 더 이상 Container에서 관리하지 않음
# Repository 중심 아키텍처에서는 Service가 직접 Repository를 사용
