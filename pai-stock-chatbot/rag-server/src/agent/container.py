# rag-server/src/agent/container.py
from dependency_injector import containers, providers
from .service import AgentService
from .graph import AgentGraphFactory

class AgentContainer(containers.DeclarativeContainer):
    """Agent 모듈 DI Container"""
    
    # === 외부 의존성 (다른 Container에서 주입) ===
    llm_service = providers.Dependency()
    stock_tools = providers.Dependency()
    
    # === Service 계층 ===
    agent_service = providers.Singleton(
        AgentService,
        llm_service=llm_service,
        tools=stock_tools
    )
    
    # === Graph Factory ===
    graph_factory = providers.Singleton(
        AgentGraphFactory,
        agent_service=agent_service
    )

def create_agent_container() -> AgentContainer:
    """Agent Container 생성"""
    return AgentContainer()