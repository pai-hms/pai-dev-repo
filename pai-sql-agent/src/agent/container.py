"""
의존성 주입 컨테이너
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Type, TypeVar
from langchain_openai import ChatOpenAI

from src.config.settings import get_settings
from src.database.connection import get_database_manager
from .settings import get_agent_config

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """의존성 주입 컨테이너 - 싱글톤"""
    
    _instance: Optional['DIContainer'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        if DIContainer._instance is not None:
            raise RuntimeError("DIContainer는 싱글톤입니다. get_instance()를 사용하세요.")
        
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'DIContainer':
        """싱글톤 인스턴스 가져오기"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """컨테이너 초기화 - App 시작시 1회만 실행"""
        if self._initialized:
            return
            
        logger.info("🏗️ DI 컨테이너 초기화 시작")
        
        # 1. 설정 서비스 등록
        settings = get_settings()
        agent_config = get_agent_config()
        self.register_singleton("settings", settings)
        self.register_singleton("agent_config", agent_config)
        
        # 2. LLM 서비스 등록
        llm = ChatOpenAI(
            model=agent_config.model_name,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
            openai_api_key=settings.openai_api_key
        )
        self.register_singleton("llm", llm)
        
        # 3. 데이터베이스 관리자 등록
        db_manager = get_database_manager()
        self.register_singleton("db_manager", db_manager)
        
        # 4. 팩토리 함수들 등록
        self._register_factories()
        
        self._initialized = True
        logger.info("✅ DI 컨테이너 초기화 완료")
    
    def register_singleton(self, name: str, instance: Any):
        """싱글톤 서비스 등록"""
        self._services[name] = instance
    
    def register_factory(self, name: str, factory: callable):
        """팩토리 함수 등록"""
        self._factories[name] = factory
    
    def get(self, name: str) -> Any:
        """서비스 인스턴스 가져오기"""
        # 싱글톤 먼저 확인
        if name in self._services:
            return self._services[name]
        
        # 팩토리로 생성
        if name in self._factories:
            instance = self._factories[name](self)
            # 팩토리로 생성된 것도 싱글톤으로 캐시
            self._services[name] = instance
            return instance
        
        raise KeyError(f"서비스 '{name}'를 찾을 수 없습니다")
    
    def _register_factories(self):
        """팩토리 함수들 등록"""
        
        def create_sql_validator(container):
            from .tools import SQLValidator
            return SQLValidator()
        
        def create_sql_executor(container):
            from .tools import SQLExecutor
            validator = container.get("sql_validator")
            db_manager = container.get("db_manager")
            return SQLExecutor(validator, db_manager)
        
        def create_sql_generator(container):
            from .tools import SQLGenerator
            llm = container.get("llm")
            return SQLGenerator(llm)
        
        def create_question_analyzer(container):
            from .nodes import QuestionAnalyzer
            llm = container.get("llm")
            return QuestionAnalyzer(llm)
        
        def create_response_generator(container):
            from .nodes import ResponseGenerator
            llm = container.get("llm")
            return ResponseGenerator(llm)
        
        # 팩토리 등록
        self.register_factory("sql_validator", create_sql_validator)
        self.register_factory("sql_executor", create_sql_executor)
        self.register_factory("sql_generator", create_sql_generator)
        self.register_factory("question_analyzer", create_question_analyzer)
        self.register_factory("response_generator", create_response_generator)


# 전역 접근 함수
async def get_container() -> DIContainer:
    """DI 컨테이너 인스턴스 가져오기"""
    return await DIContainer.get_instance()


# 편의 함수들
async def get_service(name: str) -> Any:
    """서비스 직접 가져오기"""
    container = await get_container()
    return container.get(name)
