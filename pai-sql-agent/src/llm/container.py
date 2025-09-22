"""
LLM 모듈용 간단한 의존성 주입 컨테이너
기존 코드 구조를 최대한 활용한 실용적 접근
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional
import httpx
from src.agent.settings import get_settings
from .provider import ChatModelProvider
from .service import LLMService

logger = logging.getLogger(__name__)


class LLMContainer:
    """LLM 모듈 전용 간단한 의존성 주입 컨테이너"""
    
    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        logger.info("LLM DI 컨테이너 생성")
    
    def register_singleton(self, name: str, factory: Callable) -> 'LLMContainer':
        """싱글톤 의존성 등록"""
        logger.debug(f"LLM 싱글톤 등록: {name}")
        self._factories[name] = factory
        return self
    
    async def get(self, name: str) -> Any:
        """의존성 해결"""
        # 이미 생성된 싱글톤이 있으면 반환
        if name in self._singletons:
            return self._singletons[name]
        
        # 팩토리가 없으면 오류
        if name not in self._factories:
            raise ValueError(f"LLM 의존성을 찾을 수 없습니다: {name}")
        
        # 싱글톤 생성 (동시성 제어)
        async with self._lock:
            if name not in self._singletons:
                logger.debug(f"LLM 싱글톤 인스턴스 생성: {name}")
                factory = self._factories[name]
                result = factory(self)
                
                # 비동기 팩토리 처리
                if asyncio.iscoroutine(result):
                    result = await result
                
                self._singletons[name] = result
        
        return self._singletons[name]
    
    async def initialize(self):
        """컨테이너 초기화"""
        if self._initialized:
            return
        
        logger.info("LLM DI 컨테이너 초기화 시작")
        self._configure_dependencies()
        self._initialized = True
        logger.info("LLM DI 컨테이너 초기화 완료")
    
    def _configure_dependencies(self):
        """의존성 구성 - 기존 코드 구조 활용"""
        
        # 설정
        self.register_singleton("settings", self._create_settings)
        
        # HTTP 클라이언트
        self.register_singleton("http_client", self._create_http_client)
        
        # 채팅 모델 프로바이더
        self.register_singleton("chat_model_provider", self._create_chat_model_provider)
        
        
        # LLM 서비스
        self.register_singleton("llm_service", self._create_llm_service)
    
    def _create_settings(self, container: 'LLMContainer'):
        """설정 팩토리 - Agent Settings 사용"""
        return get_settings()
    
    def _create_http_client(self, container: 'LLMContainer') -> httpx.AsyncClient:
        """HTTP 클라이언트 팩토리"""
        settings = container._singletons.get("settings")
        if not settings:
            settings = self._create_settings(container)
            container._singletons["settings"] = settings
        
        # HTTP 클라이언트 설정
        limits = httpx.Limits(
            max_keepalive_connections=getattr(settings, 'MAX_CONCURRENCY', 10),
            max_connections=getattr(settings, 'MAX_CONCURRENCY', 10),
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(getattr(settings, 'REQUEST_TIMEOUT', 30), pool=None)
        return httpx.AsyncClient(limits=limits, timeout=timeout)
    
    def _create_chat_model_provider(self, container: 'LLMContainer'):
        """채팅 모델 프로바이더 팩토리"""
        settings = container._singletons.get("settings")
        if not settings:
            settings = self._create_settings(container)
            container._singletons["settings"] = settings
        
        http_client = container._singletons.get("http_client")
        if not http_client:
            http_client = self._create_http_client(container)
            container._singletons["http_client"] = http_client
        
        return ChatModelProvider(settings, http_client)
    
    
    async def _create_llm_service(self, container: 'LLMContainer'):
        """LLM 서비스 팩토리"""
        # 의존성 해결
        chat_model_provider = await container.get("chat_model_provider")
        settings = await container.get("settings")
        
        # 서비스 생성 (의존성 주입)
        service = LLMService()
        service._chat_model_provider = chat_model_provider
        service._settings = settings
        service._initialized = True
        
        return service
    
    async def close(self):
        """컨테이너 정리"""
        logger.info("LLM DI 컨테이너 정리 시작")
        
        # HTTP 클라이언트 정리
        http_client = self._singletons.get("http_client")
        if http_client and hasattr(http_client, 'aclose'):
            await http_client.aclose()
        
        # 채팅 모델 프로바이더 정리
        chat_provider = self._singletons.get("chat_model_provider")
        if chat_provider and hasattr(chat_provider, 'aclose'):
            await chat_provider.aclose()
        
        # 생성된 인스턴스들 정리
        for name, instance in self._singletons.items():
            try:
                if hasattr(instance, 'close'):
                    await instance.close()
                elif hasattr(instance, 'cleanup'):
                    await instance.cleanup()
                logger.debug(f"LLM 인스턴스 정리 완료: {name}")
            except Exception as e:
                logger.error(f"LLM 인스턴스 정리 실패: {name}, 오류: {e}")
        
        self._singletons.clear()
        self._factories.clear()
        self._initialized = False
        logger.info("LLM DI 컨테이너 정리 완료")


# 전역 컨테이너 인스턴스
_llm_container: Optional[LLMContainer] = None
_container_lock = asyncio.Lock()


async def get_llm_container() -> LLMContainer:
    """LLM 컨테이너 싱글톤 인스턴스 반환"""
    global _llm_container
    
    if _llm_container is None:
        async with _container_lock:
            if _llm_container is None:
                _llm_container = LLMContainer()
                await _llm_container.initialize()
    
    return _llm_container


async def close_llm_container():
    """LLM 컨테이너 정리"""
    global _llm_container
    
    if _llm_container is not None:
        await _llm_container.close()
        _llm_container = None
