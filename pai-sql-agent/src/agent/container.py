"""
Agent Container - Application Layer
Clean Architecture 기반 비즈니스 로직 계층
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
    """
    Application Layer - Agent Container
    
    역할:
    - SQL Agent 비즈니스 로직 조합
    - LangGraph 워크플로우 관리
    - 도구(Tools) 및 서비스 통합
    
    의존성: Infrastructure Layer (LLM)
    """
    
    # Configuration Layer
    config = providers.Configuration()
    
    # External Infrastructure Dependencies
    llm_container = providers.Container(LLMContainer)
    
    # Domain Layer - Settings & Tools
    settings = providers.Singleton(get_settings)
    tools = providers.Object(AVAILABLE_TOOLS)
    
    # Infrastructure Layer - LangGraph Workflow
    workflow = providers.Resource(
        create_sql_agent_graph
    )
    
    # Application Layer - Agent Service (비즈니스 로직 집중점)
    agent_service = providers.Factory(
        SQLAgentService,
        workflow=workflow
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