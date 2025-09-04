# rag-server/tests/agent/test_tools.py
import pytest
from unittest.mock import patch, MagicMock
from src.agent.tools import get_stock_price, calculator, get_agent_tools

# 클래스 레벨에서 asyncio 마크 적용
@pytest.mark.asyncio
class TestAgentTools:
    """Agent Tools 테스트"""
    
    async def test_get_stock_price_success(self):
        """주가 조회 성공 테스트"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_hist = MagicMock()
            mock_hist.empty = False
            mock_hist.__getitem__.return_value.iloc.__getitem__.return_value = 150.25
            mock_ticker.return_value.history.return_value = mock_hist
            
            result = await get_stock_price.ainvoke({"symbol": "AAPL"})
            assert "AAPL: $150.25" in result
    
    async def test_get_stock_price_empty_symbol(self):
        """빈 심볼 테스트"""
        result = await get_stock_price.ainvoke({"symbol": ""})
        assert "오류: 주식 심볼이 비어있습니다." in result
    
    def test_calculator_success(self):
        """계산기 성공 테스트"""
        result = calculator.invoke({"expression": "100 * 1.5"})
        assert "100 * 1.5 = 150.0" in result
    
    def test_calculator_division_by_zero(self):
        """0으로 나누기 테스트"""
        result = calculator.invoke({"expression": "10 / 0"})
        assert "오류: 0으로 나눌 수 없습니다." in result
    
    def test_get_agent_tools(self):
        """도구 목록 테스트"""
        tools = get_agent_tools()
        assert len(tools) == 2
        assert tools[0].name == "get_stock_price"
        assert tools[1].name == "calculator"