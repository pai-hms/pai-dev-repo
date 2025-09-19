"""
Database DI Container - 비동기 리소스 지원
데이터베이스 관련 서비스들의 의존성 주입을 관리
"""
import logging
import asyncio
from dependency_injector import containers, providers

from .connection import DatabaseManager, get_database_manager
from .repository import DatabaseRepository
from .service import DatabaseService

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """Database 모듈 DI 컨테이너"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # ✅ 비동기 리소스 정의
    database_manager = providers.Resource(get_database_manager)
    
    # Repository Layer - 세션 팩토리를 통한 생성
    # 주의: DatabaseRepository는 실제로는 세션 컨텍스트에서 생성되어야 함
    
    # Service Layer - DatabaseManager를 통한 생성
    database_service = providers.Factory(
        DatabaseService,
        database_manager=database_manager
    )


# 전역 컨테이너 인스턴스
container = DatabaseContainer()

# ✅ 비동기 초기화 상태 관리
_initialized = False
_init_lock = asyncio.Lock()


async def initialize_container():
    """컨테이너 비동기 리소스 초기화"""
    global _initialized
    
    if _initialized:
        return
        
    async with _init_lock:
        if _initialized:
            return
            
        logger.info("🔧 DI 컨테이너 비동기 리소스 초기화 시작")
        
        try:
            # ✅ 핵심: 비동기 리소스들을 먼저 초기화
            await container.init_resources()
            
            _initialized = True
            logger.info("✅ DI 컨테이너 비동기 리소스 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ DI 컨테이너 초기화 실패: {e}")
            raise


async def get_database_container() -> DatabaseContainer:
    """데이터베이스 컨테이너 인스턴스 반환"""
    await initialize_container()
    return container


async def get_database_service_from_container() -> DatabaseService:
    """데이터베이스 서비스 인스턴스 반환 (비동기)"""
    await initialize_container()  # ✅ 먼저 비동기 리소스 초기화
    
    try:
        # ✅ 초기화된 후에는 동기적으로 접근 가능
        service = container.database_service()
        logger.info("✅ 데이터베이스 서비스 반환 완료")
        return service
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 서비스 생성 실패: {e}")
        raise


async def get_database_manager_from_container() -> DatabaseManager:
    """데이터베이스 매니저 반환 (비동기)"""
    await initialize_container()
    return container.database_manager()


# DatabaseRepository는 세션 컨텍스트에서만 생성되므로 컨테이너에서 직접 제공하지 않음


async def cleanup_container():
    """컨테이너 리소스 정리 (비동기)"""
    global _initialized
    
    if _initialized:
        logger.info("🧹 DI 컨테이너 비동기 리소스 정리 시작")
        
        try:
            await container.shutdown_resources()
            _initialized = False
            logger.info("✅ DI 컨테이너 비동기 리소스 정리 완료")
            
        except Exception as e:
            logger.error(f"❌ 리소스 정리 중 오류: {e}")
            raise


async def reset_container():
    """컨테이너 리셋 (개발/테스트용)"""
    await cleanup_container()
    await initialize_container()
    logger.info("🔄 DI 컨테이너 리셋 완료")
