"""
Session DI Container - dependency-injector 사용
세션 관리 관련 서비스들의 의존성 주입을 관리
"""
import logging
from dependency_injector import containers, providers

from src.database.connection import get_database_manager
from .repository import SessionRepository
from .service import SessionService

logger = logging.getLogger(__name__)


class SessionContainer(containers.DeclarativeContainer):
    """Session 모듈 DI 컨테이너"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # 데이터베이스 매니저 (외부 의존성)
    database_manager = providers.Resource(get_database_manager)
    
    # Repository Layer
    session_repository = providers.Factory(
        SessionRepository,
        database_manager=database_manager
    )
    
    # Service Layer
    session_service = providers.Factory(
        SessionService,
        repository=session_repository
    )


# 전역 컨테이너 인스턴스
container = SessionContainer()


async def get_session_container() -> SessionContainer:
    """세션 컨테이너 인스턴스 반환"""
    return container


async def get_session_repository() -> SessionRepository:
    """세션 리포지토리 인스턴스 반환"""
    return container.session_repository()


async def get_session_service_from_container() -> SessionService:
    """컨테이너에서 세션 서비스 인스턴스 반환"""
    return container.session_service()
