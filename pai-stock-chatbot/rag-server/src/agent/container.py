# rag-server/src/agent/container.py
from dependency_injector import containers, providers
from .service import AgentService
from .graph import AgentGraphFactory
from .nodes import AgentNodes

class AgentContainer(containers.DeclarativeContainer):
    """Agent 모듈 DI Container"""
    
    # === External Dependencies ===
    llm_service = providers.Dependency()
    stock_tools = providers.Dependency()
    
    # === Service ===
    service = providers.Singleton(
        AgentService,
        llm_service=llm_service,
        tools=stock_tools
    )
    
    # === Nodes ===
    nodes = providers.Singleton(
        AgentNodes,
        agent_service=service
    )
    
    # === Graph Factory ===
    graph_factory = providers.Singleton(
        AgentGraphFactory,
        agent_service=service
    )
    
    # === Executor ===
    executor = providers.Singleton(
        lambda factory: factory.create_executor(),
        factory=graph_factory
    )

def create_agent_container() -> AgentContainer:
    return AgentContainer()