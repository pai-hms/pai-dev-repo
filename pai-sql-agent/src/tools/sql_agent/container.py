"""
SQL Agent 전용 의존성 주입 컨테이너
SQL 분석 전문 도구의 의존성 관리

설계 원칙:
- 단일 책임 원칙: SQL 관련 의존성만 관리
- 의존성 주입: 외부 서비스들을 주입받아 사용
"""
import asyncio
from typing import Optional
from src.llm.service import get_llm_service
from src.agent.settings import AgentSettings, create_agent_settings
from src.database.connection import get_database_manager


class SQLAgentContainer:
    """SQL Agent 의존성 컨테이너"""
    
    _instance: Optional['SQLAgentContainer'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._settings = None
        self._llm_service = None
        self._db_manager = None
        self._sql_agent = None
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'SQLAgentContainer':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """컨테이너 초기화"""
        if self._initialized:
            return
        
        # 설정 초기화
        self._settings = await create_agent_settings()
        
        # LLM 서비스 초기화
        self._llm_service = await get_llm_service()
        
        # 데이터베이스 매니저 초기화
        self._db_manager = await get_database_manager()
        
        # SQL Agent 그래프 생성
        from .graph import create_sql_agent
        self._sql_agent = await create_sql_agent(
            settings=self._settings,
            llm_service=self._llm_service,
            db_manager=self._db_manager
        )
        
        self._initialized = True
    
    async def get_sql_agent_service(self):
        """SQL Agent 서비스 반환"""
        if not self._initialized:
            await self._initialize()
        return self._sql_agent
    
    async def get_settings(self) -> AgentSettings:
        """설정 반환"""
        if not self._initialized:
            await self._initialize()
        return self._settings
    
    async def get_llm_service(self):
        """LLM 서비스 반환"""
        if not self._initialized:
            await self._initialize()
        return self._llm_service
    
    async def get_database_manager(self):
        """데이터베이스 매니저 반환"""
        if not self._initialized:
            await self._initialize()
        return self._db_manager


# 전역 접근 함수
async def get_sql_agent_container() -> SQLAgentContainer:
    """SQL Agent 컨테이너 인스턴스 반환"""
    return await SQLAgentContainer.get_instance()


async def get_sql_agent_service():
    """SQL Agent 서비스 인스턴스 반환"""
    container = await get_sql_agent_container()
    return await container.get_sql_agent_service()