"""
Application Container - 간결화된 최상위 조합자 (순환참조 제거)
Infrastructure Layer 중심 구성
"""
import logging
from dependency_injector import containers, providers
from src.agent.container import AgentContainer
from src.llm.container import LLMContainer
from src.database.container import DatabaseContainer

logger = logging.getLogger(__name__)


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Clean Architecture - Application Container (간결화)
    
    Infrastructure Layer 중심:
    1. Database: 세션 팩토리 관리
    2. LLM: 모델 및 서비스 관리
    3. Agent: 워크플로우 관리
    
    Service Layer는 독립적 생성으로 순환참조 제거
    """
    
    # Configuration Layer
    config = providers.Configuration()
    
    # Infrastructure Layer (기반 인프라)
    database = providers.Container(DatabaseContainer)  # 세션 팩토리
    llm = providers.Container(LLMContainer)            # LLM 관리
    agent = providers.Container(AgentContainer, llm_container=llm)  # 워크플로우


