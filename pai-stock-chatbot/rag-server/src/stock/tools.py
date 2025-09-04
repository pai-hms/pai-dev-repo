# rag-server/src/stock/tools.py
from langchain_core.tools import tool
from typing import List
from .services import StockService

class StockToolsFactory:
    """Stock 도구 팩토리"""
    
    def __init__(self, stock_service: StockService):
        """완전한 의존성 주입"""
        self._stock_service = stock_service
    
    def create_tools(self) -> List:
        """도구 목록 생성"""
        @tool
        async def get_stock_price(symbol: str) -> str:
            """주식 가격을 조회합니다."""
            result = await self._stock_service.get_stock_price(symbol)
            return str(result)

        @tool
        def calculator(expression: str) -> str:
            """수학 계산을 수행합니다."""
            return self._stock_service.calculate(expression)

        return [get_stock_price, calculator]