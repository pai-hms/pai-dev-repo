"""
Agent 모듈용 간단한 의존성 주입 컨테이너
기존 코드 구조를 최대한 활용한 실용적 접근
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional
from .settings import get_settings
from src.llm.service import get_llm_service
from .tools import AVAILABLE_TOOLS
from .graph import create_sql_agent_graph
from .service import SQLAgentService

logger = logging.getLogger(__name__)


class AgentContainer:
    """Agent 모듈 전용 간단한 의존성 주입 컨테이너"""
    
    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        logger.info("Agent DI 컨테이너 생성")
    
    def register_singleton(self, name: str, factory: Callable) -> 'AgentContainer':
        """싱글톤 의존성 등록"""
        logger.debug(f"싱글톤 등록: {name}")
        self._factories[name] = factory
        return self
    
    async def get(self, name: str) -> Any:
        """의존성 해결"""
        logger.info(f"의존성 요청: {name}")
        
        # 이미 생성된 싱글톤이 있으면 반환
        if name in self._singletons:
            logger.info(f"기존 싱글톤 반환: {name}")
            return self._singletons[name]
        
        # 팩토리가 없으면 오류
        if name not in self._factories:
            raise ValueError(f"의존성을 찾을 수 없습니다: {name}")
        
        # 싱글톤 생성 (재귀 호출 방지)
        logger.info(f"싱글톤 생성 시작: {name}")
        
        # 더블 체크 (락 없이)
        if name not in self._singletons:
            logger.info(f"팩토리 호출: {name}")
            factory = self._factories[name]
            result = factory(self)
            
            # 비동기 팩토리 처리
            if asyncio.iscoroutine(result):
                logger.info(f"비동기 팩토리 대기: {name}")
                result = await result
                logger.info(f"비동기 팩토리 완료: {name}")
            
            self._singletons[name] = result
            logger.info(f"싱글톤 등록 완료: {name}")
        
        return self._singletons[name]
    
    async def initialize(self):
        """컨테이너 초기화"""
        if self._initialized:
            return
        
        logger.info("Agent DI 컨테이너 초기화 시작")
        self._configure_dependencies()
        self._initialized = True
        logger.info("Agent DI 컨테이너 초기화 완료")
    
    def _configure_dependencies(self):
        """의존성 구성 - 기존 코드 구조 활용"""
        
        # 설정
        self.register_singleton("settings", self._create_settings)
        
        # LLM 서비스
        self.register_singleton("llm_service", self._create_llm_service)
        
        # 도구들
        self.register_singleton("tools", self._create_tools)
        
        # 워크플로우
        self.register_singleton("workflow", self._create_workflow)
        
        # 에이전트 서비스
        self.register_singleton("agent_service", self._create_agent_service)
    
    async def _create_settings(self, container: 'AgentContainer'):
        """설정 팩토리"""
        return get_settings()
    
    async def _create_llm_service(self, container: 'AgentContainer'):
        """LLM 서비스 팩토리"""
        return await get_llm_service()
    
    async def _create_tools(self, container: 'AgentContainer'):
        """도구 팩토리"""
        return AVAILABLE_TOOLS
    
    async def _create_workflow(self, container: 'AgentContainer'):
        """워크플로우 팩토리"""
        logger.info("워크플로우 팩토리 시작")
        workflow = await create_sql_agent_graph()
        logger.info("워크플로우 팩토리 완료")
        return workflow
    
    async def _create_agent_service(self, container: 'AgentContainer'):
        """에이전트 서비스 팩토리 - 순환 의존성 방지"""
        logger.info("Agent 서비스 팩토리 시작")
        
        # 워크플로우 없이 서비스 생성 (순환 의존성 방지)
        logger.info("SQL Agent 서비스 인스턴스 생성 시작 (워크플로우 없이)")
        service = SQLAgentService(workflow=None)
        logger.info("SQL Agent 서비스 생성 완료")
        
        # 워크플로우 별도 설정
        logger.info("워크플로우 의존성 해결 시작")
        workflow = await container.get("workflow")
        logger.info("워크플로우 의존성 해결 완료")
        
        logger.info("서비스에 워크플로우 주입")
        service.set_workflow(workflow)
        logger.info("워크플로우 주입 완료")
        
        return service
    
    async def close(self):
        """컨테이너 정리"""
        logger.info("Agent DI 컨테이너 정리 시작")
        
        # 생성된 인스턴스들 정리
        for name, instance in self._singletons.items():
            try:
                if hasattr(instance, 'close'):
                    await instance.close()
                elif hasattr(instance, 'cleanup'):
                    await instance.cleanup()
                logger.debug(f"인스턴스 정리 완료: {name}")
            except Exception as e:
                logger.error(f"인스턴스 정리 실패: {name}, 오류: {e}")
        
        self._singletons.clear()
        self._factories.clear()
        self._initialized = False
        logger.info("Agent DI 컨테이너 정리 완료")


# 전역 컨테이너 인스턴스
_agent_container: Optional[AgentContainer] = None
_container_lock = asyncio.Lock()


async def get_agent_container() -> AgentContainer:
    """Agent 컨테이너 싱글톤 인스턴스 반환"""
    global _agent_container
    
    if _agent_container is None:
        async with _container_lock:
            if _agent_container is None:
                _agent_container = AgentContainer()
                await _agent_container.initialize()
    
    return _agent_container


async def close_agent_container():
    """Agent 컨테이너 정리"""
    global _agent_container
    
    if _agent_container is not None:
        await _agent_container.close()
        _agent_container = None
