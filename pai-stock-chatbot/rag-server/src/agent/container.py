# rag-server/src/agent/container.py
from dependency_injector import containers, providers
from .service import AgentService
from .graph import AgentGraphFactory
from ..llm.container import LLMContainer

class AgentContainer(containers.DeclarativeContainer):
    """Agent 모듈 DI Container"""

    # LLM Container 의존성
    llm_container = providers.DependenciesContainer()
    
    # === Service (Tools 내장) ===
    service = providers.Singleton(
        AgentService,
        llm_service=llm_container.service
    )
    
    # === Graph Factory (Service 전달) ===
    graph_factory = providers.Singleton(
        AgentGraphFactory,
        agent_service=service  # nodes가 아닌 agent_service
    )
    
    # === Executor ===
    executor = providers.Singleton(
        lambda factory: factory.create_executor(),
        factory=graph_factory
    )

def create_agent_container(llm_container: LLMContainer) -> AgentContainer:
    container = AgentContainer()
    container.llm_container.override(llm_container)
    return container