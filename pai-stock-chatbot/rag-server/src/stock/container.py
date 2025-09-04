# rag-server/src/stock/container.py
from dependency_injector import containers, providers
from .repository import StockRepository
from .services import StockService
from .tools import StockToolsFactory

class StockContainer(containers.DeclarativeContainer):
    """Stock 모듈 DI Container - 완전한 DI"""
    
    # === Repository ===
    repository = providers.Singleton(StockRepository)
    
    # === Service ===
    service = providers.Singleton(
        StockService,
        repository=repository
    )
    
    # === Tools Factory ===
    tools_factory = providers.Singleton(
        StockToolsFactory,
        stock_service=service
    )
    
    # === Tools ===
    tools = providers.Singleton(
        lambda factory: factory.create_tools(),
        factory=tools_factory
    )

def create_stock_container() -> StockContainer:
    return StockContainer()