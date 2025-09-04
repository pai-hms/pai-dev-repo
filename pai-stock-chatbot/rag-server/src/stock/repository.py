# rag-server/src/stock/repository.py
from typing import Dict, Optional
from datetime import datetime, timedelta
import yfinance as yf

class StockPriceCache:
    """주가 캐시 데이터"""
    def __init__(self, price: float, timestamp: datetime):
        self.price = price
        self.timestamp = timestamp
    
    def is_expired(self, ttl_minutes: int = 5) -> bool:
        """캐시 만료 여부 확인"""
        return datetime.now() - self.timestamp > timedelta(minutes=ttl_minutes)

class StockRepository:
    """주식 데이터 저장소 - 데이터 주권 담당"""
    
    def __init__(self):
        self._price_cache: Dict[str, StockPriceCache] = {}
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        """캐시된 주가 조회"""
        cache = self._price_cache.get(symbol)
        if cache and not cache.is_expired():
            return cache.price
        return None
    
    def cache_price(self, symbol: str, price: float) -> None:
        """주가 캐시 저장"""
        self._price_cache[symbol] = StockPriceCache(price, datetime.now())
    
    def fetch_live_price(self, symbol: str) -> float:
        """실시간 주가 조회"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            raise ValueError(f"'{symbol}'에 대한 데이터를 찾을 수 없습니다.")
        return round(hist['Close'].iloc[-1], 2)