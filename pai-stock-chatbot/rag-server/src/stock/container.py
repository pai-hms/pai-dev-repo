# rag-server/src/stock/container.py
from dependency_injector import containers, providers
from .repository import StockRepository
from .services import StockService

class StockContainer(containers.DeclarativeContainer):
    """Stock 모듈 DI Container"""
    
    # === Repository 계층 ===
    stock_repository = providers.Singleton(StockRepository)
    
    # === Service 계층 ===
    stock_service = providers.Singleton(
        StockService,
        repository=stock_repository
    )

def create_stock_container() -> StockContainer:
    """Stock Container 생성"""
    return StockContainer()