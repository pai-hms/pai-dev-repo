# rag-server/src/agent/tools.py
from langchain_core.tools import tool
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import yfinance as yf
import numexpr
import asyncio

class StockPriceCache:
    """간단한 주가 캐시"""
    def __init__(self):
        self._cache: Dict[str, tuple[float, datetime]] = {}
    
    def get(self, symbol: str) -> Optional[float]:
        if symbol in self._cache:
            price, timestamp = self._cache[symbol]
            if datetime.now() - timestamp < timedelta(minutes=5):
                return price
        return None
    
    def set(self, symbol: str, price: float):
        self._cache[symbol] = (price, datetime.now())

# 전역 캐시 인스턴스 (싱글톤 패턴)
_stock_cache = StockPriceCache()

@tool
async def get_stock_price(symbol: str) -> str:
    """주식 가격을 조회합니다.
    
    Args:
        symbol: 주식 심볼 (예: AAPL, GOOGL)
    
    Returns:
        주식 가격 정보 문자열
    """
    if not symbol or symbol.strip() == "":
        return "오류: 주식 심볼이 비어있습니다."
    
    try:
        # 캐시 확인
        cached_price = _stock_cache.get(symbol.upper())
        if cached_price is not None:
            return f"{symbol.upper()}: ${cached_price:.2f}"
        
        # 실시간 조회
        def fetch_price():
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if hist.empty:
                raise ValueError(f"'{symbol}'에 대한 데이터를 찾을 수 없습니다.")
            return round(hist['Close'].iloc[-1], 2)
        
        price = await asyncio.to_thread(fetch_price)
        _stock_cache.set(symbol.upper(), price)
        
        return f"{symbol.upper()}: ${price:.2f}"
        
    except Exception as e:
        return f"주가 조회 오류: {e}"

@tool
def calculator(expression: str) -> str:
    """수학 계산을 수행합니다.
    
    Args:
        expression: 계산할 수식 (예: "100 * 1.5", "2 + 3 * 4")
    
    Returns:
        계산 결과
    """
    if not expression or expression.strip() == "":
        return "오류: 계산식이 비어있습니다."
    
    try:
        result = numexpr.evaluate(expression)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "오류: 0으로 나눌 수 없습니다."
    except Exception as e:
        return f"계산 오류: {e}"

def get_agent_tools() -> List:
    """Agent에서 사용할 도구 목록"""
    return [get_stock_price, calculator]