"""
DI 컨테이너 - 완전 비동기 버전
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from src.config.settings import get_settings
from src.database.connection import get_database_manager

logger = logging.getLogger(__name__)


class DIContainer:
    """의존성 주입 컨테이너 (완전 비동기)"""
    
    _instance: Optional['DIContainer'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        if DIContainer._instance is not None:
            raise RuntimeError("DIContainer는 싱글톤입니다.")
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'DIContainer':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """컨테이너 초기화 (완전 비동기)"""
        if self._initialized:
            return
            
        logger.info("🚀 DI 컨테이너 초기화 시작")
        
        try:
            # 설정 (비동기)
            settings = get_settings()
            
            # Agent 설정 (비동기)
            from src.agent.settings import get_agent_settings
            agent_settings = await get_agent_settings()
            
            self._services["settings"] = settings
            self._services["agent_settings"] = agent_settings
            
            # 데이터베이스 (비동기)
            database_manager = await get_database_manager()
            self._services["database_manager"] = database_manager
            
            # 세션 서비스 (비동기)
            try:
                from src.session.container import get_session_service
                session_service = await get_session_service()
                self._services["session_service"] = session_service
            except Exception as e:
                logger.warning(f"⚠️ 세션 서비스 초기화 실패: {e}")
                self._services["session_service"] = None
            
            # 에이전트 그래프 (비동기)
            try:
                from .graph import create_sql_agent_graph
                agent_graph = await create_sql_agent_graph()
                self._services["agent_graph"] = agent_graph
            except Exception as e:
                logger.warning(f"⚠️ 에이전트 그래프 초기화 실패: {e}")
                self._services["agent_graph"] = None
            
            # LLM 서비스 (비동기)
            try:
                from src.llm.service import get_llm_service
                llm_service = await get_llm_service()
                self._services["llm_service"] = llm_service
            except Exception as e:
                logger.warning(f"⚠️ LLM 서비스 초기화 실패: {e}")
                self._services["llm_service"] = None
            
            self._initialized = True
            logger.info("✅ DI 컨테이너 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ DI 컨테이너 초기화 실패: {e}")
            raise
    
    async def get(self, service_name: str) -> Any:
        """서비스 인스턴스 반환 (비동기)"""
        if not self._initialized:
            await self._initialize()
        
        if service_name not in self._services:
            raise KeyError(f"서비스 '{service_name}'을 찾을 수 없습니다.")
        
        return self._services[service_name]
    
    async def cleanup(self):
        """컨테이너 정리 (비동기)"""
        logger.info("🧹 DI 컨테이너 정리")
        
        if "database_manager" in self._services:
            db_manager = self._services["database_manager"]
            if hasattr(db_manager, 'cleanup'):
                try:
                    await db_manager.cleanup()
                except Exception as e:
                    logger.warning(f"⚠️ 데이터베이스 정리 실패: {e}")
        
        self._services.clear()
        self._initialized = False


# 전역 컨테이너 (비동기)
_container: Optional[DIContainer] = None


async def get_container() -> DIContainer:
    """DI 컨테이너 반환 (비동기)"""
    global _container
    if _container is None:
        _container = await DIContainer.get_instance()
    return _container


async def get_service(service_name: str) -> Any:
    """서비스 가져오기 (비동기)"""
    container = await get_container()
    return await container.get(service_name)


async def cleanup_container():
    """DI 컨테이너 정리 (비동기)"""
    global _container
    if _container:
        await _container.cleanup()
        _container = None
