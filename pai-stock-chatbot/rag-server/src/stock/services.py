# rag-server/src/stock/services.py
import asyncio
import yfinance as yf
import numexpr

class StockService:
    """주식 비즈니스 서비스"""
    
    def _fetch_price(self, symbol: str) -> float:
        """동기 방식으로 주가 조회"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            raise ValueError(f"'{symbol}'에 대한 데이터를 찾을 수 없습니다.")
        return round(hist['Close'].iloc[-1], 2)

    async def get_stock_price(self, symbol: str) -> float | str:
        """주식 가격 조회"""
        try:
            price = await asyncio.to_thread(self._fetch_price, symbol)
            return price
        except Exception as e:
            return f"주가 조회 중 오류가 발생했습니다: {e}"
    
    def calculate(self, expression: str) -> str:
        """수학 계산"""
        return str(numexpr.evaluate(expression))
