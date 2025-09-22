"""
Agent 모듈용 의존성 주입 컨테이너 - dependency-injector 사용
"""
import logging
from dependency_injector import containers, providers
from .settings import get_settings
from .tools import AVAILABLE_TOOLS
from .graph import create_sql_agent_graph
from .service import SQLAgentService
from src.llm.container import LLMContainer

logger = logging.getLogger(__name__)


class AgentContainer(containers.DeclarativeContainer):
    """Agent 모듈용 의존성 주입 컨테이너"""
    
    # Configuration
    config = providers.Configuration()
    
    # External containers
    llm = providers.Container(LLMContainer)
    
    # Settings
    settings = providers.Singleton(get_settings)
    
    # Tools
    tools = providers.Object(AVAILABLE_TOOLS)
    
    # Workflow (Resource for lifecycle management)
    workflow = providers.Resource(
        create_sql_agent_graph,
        # 필요한 의존성들을 여기에 주입할 수 있음
    )
    
    # Agent Service (Factory로 변경하여 매번 새로운 인스턴스 생성)
    agent_service = providers.Factory(
        SQLAgentService
    )


# 전역 컨테이너 인스턴스
_agent_container = None


def get_agent_container() -> AgentContainer:
    """Agent 컨테이너 싱글톤 인스턴스 반환"""
    global _agent_container
    
    if _agent_container is None:
        _agent_container = AgentContainer()
        logger.info("Agent DI 컨테이너 생성 완료")
    
    return _agent_container


async def close_agent_container():
    """Agent 컨테이너 정리"""
    global _agent_container
    
    if _agent_container is not None:
        # Resource 정리
        try:
            await _agent_container.shutdown_resources()
        except Exception as e:
            logger.error(f"Agent 리소스 정리 실패: {e}")
        
        _agent_container = None
        logger.info("Agent DI 컨테이너 정리 완료")