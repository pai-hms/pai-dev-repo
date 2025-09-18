"""
세션 관련 DI 컨테이너
의존성 주입을 위한 컨테이너 클래스
"""
import asyncio
import logging
from typing import Any, Optional
from datetime import datetime

from .domains import AgentSession
from .entities import AgentSessionEntity
from .repository import SessionRepository
from .service import SessionService

logger = logging.getLogger(__name__)


class SessionContainer:
    """세션 관련 DI 컨테이너 - 싱글톤"""

    _instance: Optional['SessionContainer'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        if SessionContainer._instance is not None:
            raise RuntimeError("SessionContainer는 싱글톤입니다. get_instance()를 사용하세요.")
        
        self._services = {}
        self._db_manager = None

    @classmethod
    async def get_instance(cls) -> 'SessionContainer':
        """싱글톤 인스턴스 가져오기"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """컨테이너 초기화"""
        logger.info("🚀 Session 컨테이너 초기화 시작")

        # DB 매니저 초기화 (비동기로 변경)
        from src.database.connection import get_database_manager
        self._db_manager = await get_database_manager()
        self._services["db_manager"] = self._db_manager

        # 팩토리 등록
        self._register_factories()

        logger.info("✅ Session 컨테이너 초기화 완료")

    def _register_factories(self):
        """서비스 팩토리 등록"""

        def create_session_repository():
            """세션 리포지토리 팩토리"""
            db_manager = self._services["db_manager"]
            return SessionRepository(db_manager)

        async def create_session_service():
            """세션 서비스 팩토리"""
            session_repo = await self.get("session_repository")
            return SessionService(session_repo)

        self._services["session_repository_factory"] = create_session_repository
        self._services["session_service_factory"] = create_session_service

    async def get(self, name: str):
        """서비스 인스턴스 반환"""
        # 이미 생성된 인스턴스 반환
        if name in self._services and not name.endswith("_factory"):
            return self._services[name]

        # 팩토리로 생성
        factory = self._services.get(f"{name}_factory")
        if factory:
            instance = factory()
            if asyncio.iscoroutine(instance):
                instance = await instance
            # 생성된 인스턴스를 캐시에 저장
            self._services[name] = instance
            return instance

        raise KeyError(f"서비스 '{name}'을 찾을 수 없습니다")

    def register_singleton(self, name: str, instance):
        """싱글톤 서비스 등록"""
        self._services[name] = instance


# 헬퍼 함수들 (편의성)
async def get_session_service() -> SessionService:
    """세션 서비스 인스턴스 반환"""
    container = await SessionContainer.get_instance()
    return await container.get("session_service")


async def get_session_repository() -> SessionRepository:
    """세션 리포지토리 인스턴스 반환"""
    container = await SessionContainer.get_instance()
    return await container.get("session_repository")


async def get_session_container() -> SessionContainer:
    """세션 컨테이너 인스턴스 반환"""
    return await SessionContainer.get_instance()
