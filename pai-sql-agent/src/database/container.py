"""
Database DI Container - Infrastructure Layer
세션 팩토리 및 데이터베이스 연결 관리
"""
import logging
from dependency_injector import containers, providers

from .settings import get_database_settings
from .session_factory import DatabaseSessionFactory

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """데이터베이스 Infrastructure Layer 컨테이너 - 순환참조 제거"""
    
    # 1. 설정 주입 (싱글톤)
    settings = providers.Singleton(get_database_settings)
    
    # 2. 세션 팩토리 인스턴스 (리소스로 생명주기 관리)
    session_factory_instance = providers.Resource(
        DatabaseSessionFactory,
        settings=settings
    )
    
    # 3. 세션 팩토리 함수 (호출 가능한 컨텍스트 매니저)
    session_factory = providers.Callable(
        lambda factory_instance: factory_instance.get_session,
        factory_instance=session_factory_instance
    )


# 전역 컨테이너 인스턴스
_database_container: DatabaseContainer = None


async def get_database_container() -> DatabaseContainer:
    """데이터베이스 컨테이너 인스턴스 반환 (비동기 초기화)"""
    global _database_container
    if _database_container is None:
        _database_container = DatabaseContainer()
        
        # 리소스 초기화
        try:
            init_result = _database_container.init_resources()
            if init_result is not None:
                await init_result
            logger.info("Database DI 컨테이너 생성 및 초기화 완료")
        except Exception as e:
            logger.error(f"Database 컨테이너 초기화 실패: {e}")
            _database_container = None
            raise
    
    return _database_container


async def close_database_container():
    """데이터베이스 컨테이너 정리"""
    global _database_container
    if _database_container is not None:
        try:
            # 리소스 정리 (세션 팩토리 등)
            shutdown_result = _database_container.shutdown_resources()
            if shutdown_result is not None:
                await shutdown_result
            logger.info("Database 컨테이너 리소스 정리 완료")
        except Exception as e:
            logger.warning(f"Database 컨테이너 정리 중 오류: {e}")
        
        _database_container = None
        logger.info("Database DI 컨테이너 정리 완료")
