"""
Tool Agent DI 컨테이너
의존성 주입을 통한 서비스 관리

설계 원칙:
- 의존성 주입: 모든 서비스 간 의존성을 중앙에서 관리
- 싱글톤 패턴: 애플리케이션 생명주기와 동일한 컨테이너 생명주기
"""
import asyncio
from typing import Optional
from src.database.connection import get_database_manager
from src.tools.repository import ToolAgentRepository
from src.tools.service import ToolAgentService
from src.tools.sql_agent.container import SQLAgentContainer


class ToolContainer:
    """Tool Agent 의존성 주입 컨테이너"""
    
    _instance: Optional['ToolContainer'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._repository = None
        self._service = None
        self._sql_agent_container = None
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'ToolContainer':
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
        
        # 데이터베이스 매니저 가져오기
        db_manager = await get_database_manager()
        
        # Repository 초기화
        self._repository = ToolAgentRepository(db_manager.get_async_session)
        
        # SQL Agent 컨테이너 초기화
        self._sql_agent_container = await SQLAgentContainer.get_instance()
        
        # Service 초기화
        self._service = ToolAgentService(
            repository=self._repository,
            sql_agent=self._sql_agent_container
        )
        
        self._initialized = True
    
    async def get_tool_agent_service(self) -> ToolAgentService:
        """Tool Agent 서비스 반환"""
        if not self._initialized:
            await self._initialize()
        return self._service
    
    async def get_tool_agent_repository(self) -> ToolAgentRepository:
        """Tool Agent 레포지토리 반환"""
        if not self._initialized:
            await self._initialize()
        return self._repository


# 전역 접근 함수
async def get_tool_container() -> ToolContainer:
    """Tool 컨테이너 인스턴스 반환"""
    return await ToolContainer.get_instance()


async def get_tool_agent_service() -> ToolAgentService:
    """Tool Agent 서비스 인스턴스 반환"""
    container = await get_tool_container()
    return await container.get_tool_agent_service()