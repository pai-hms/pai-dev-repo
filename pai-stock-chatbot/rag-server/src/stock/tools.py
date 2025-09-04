# rag-server/src/stock/tools.py
from langchain_core.tools import tool
from .services import StockService

stock_service = StockService()

@tool
async def get_stock_price(symbol: str) -> float | str:
    """주식 가격 조회 도구"""
    return await stock_service.get_stock_price(symbol)

@tool
def calculator(expression: str) -> str:
    """계산 도구"""
    return stock_service.calculate(expression)

stock_tools = [get_stock_price, calculator]
