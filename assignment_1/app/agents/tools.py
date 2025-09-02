# app/agents/tools.py
import asyncio
import yfinance as yf
from langchain_core.tools import tool
import numexpr

def _get_current_stock_price(symbol: str) -> float | str:
    """yfinance 라이브러리를 호출하는 동기 함수"""
    try:
        ticker = yf.Ticker(symbol)
        # 하루 동안의 데이터를 가져와 마지막 종가를 확인
        hist = ticker.history(period="1d")
        if hist.empty:
            return f"'{symbol}'에 대한 데이터를 찾을 수 없습니다. 주식 심볼이 정확한지 확인해주세요."
        return round(hist['Close'].iloc[-1], 2)
    except Exception as e:
        return f"주가 조회 중 오류가 발생했습니다: {e}"

@tool
async def get_stock_price(symbol: str) -> float | str:
    """
    주어진 주식 심볼(예: AAPL, GOOG)의 현재 가격을 조회합니다.
    yfinance 라이브러리를 사용하여 실시간 데이터를 가져옵니다.
    """
    print(f"--- TOOL: yfinance 주가 조회 ({symbol}) ---")
    
    # 동기 함수인 _get_current_stock_price를 별도 스레드에서 실행하여
    # 메인 이벤트 루프를 막지 않도록 합니다.
    price_or_error = await asyncio.to_thread(_get_current_stock_price, symbol)
    
    return price_or_error

@tool(parse_docstring=True)
def calculator(expression: str) -> str:
    """Calculate expression using Python's numexpr library.

    Args:
        expression (str): A single-line mathematical expression to evaluate. For example: "37593 * 67" or "37593**(1/5)".

    Returns:
        str: The result of the evaluated expression.
    """
    return str(numexpr.evaluate(expression))


stock_tools = [
    get_stock_price, 
    calculator
]
