# rag-server/src/stock/services.py
import asyncio
import numexpr
from .repository import StockRepository

class StockService:
    """주식 비즈니스 서비스"""
    
    def __init__(self, repository: StockRepository = None):
        self._repository = repository or StockRepository()

    async def get_stock_price(self, symbol: str) -> float | str:
        """주식 가격 조회 (캐시 우선)"""
        try:
            # 캐시 확인
            cached_price = self._repository.get_cached_price(symbol)
            if cached_price is not None:
                return cached_price
            
            # 실시간 조회 및 캐시 저장
            price = await asyncio.to_thread(self._repository.fetch_live_price, symbol)
            self._repository.cache_price(symbol, price)
            return price
        except Exception as e:
            return f"주가 조회 중 오류가 발생했습니다: {e}"
    
    def calculate(self, expression: str) -> str:
        """수학 계산"""
        return str(numexpr.evaluate(expression))