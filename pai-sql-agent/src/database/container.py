"""
Database DI Container - 단순화된 Repository 중심 구조
Repository가 데이터 제어권을 담당하는 아키텍처
"""
import logging
import asyncio
from dependency_injector import containers, providers

from .connection import get_database_manager

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """Database 모듈 DI 컨테이너 - 단순화"""
    
    # 기본 설정
    config = providers.Configuration()
    
    # ✅ DatabaseManager만 관리 (Repository는 세션별로 생성)
    database_manager = providers.Resource(get_database_manager)


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


async def get_database_manager_from_container():
    """데이터베이스 매니저 반환 (비동기)"""
    await initialize_container()
    return container.database_manager()


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


# ✅ DatabaseService는 더 이상 Container에서 관리하지 않음
# Repository 중심 아키텍처에서는 Service가 직접 DatabaseManager를 사용
