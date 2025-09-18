"""
Database DI Container - dependency-injector 사용
데이터베이스 관련 서비스들의 의존성 주입을 관리
"""
import logging
from dependency_injector import containers, providers

from .connection import DatabaseManager, get_database_manager
from .repository import DatabaseService as DatabaseRepository
from .service import DatabaseService

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """Database 모듈 DI 컨테이너"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # 데이터베이스 매니저
    database_manager = providers.Resource(get_database_manager)
    
    # Repository Layer - ✅ 수정: 비동기 세션 처리
    database_repository = providers.Factory(
        DatabaseRepository,
        database_manager=database_manager
    )
    
    # Service Layer  
    database_service = providers.Factory(
        DatabaseService,
        repository=database_repository
    )


# 전역 컨테이너 인스턴스
container = DatabaseContainer()


async def get_database_container() -> DatabaseContainer:
    """데이터베이스 컨테이너 인스턴스 반환"""
    return container


async def get_database_service() -> DatabaseService:
    """데이터베이스 서비스 인스턴스 반환"""
    return container.database_service()
