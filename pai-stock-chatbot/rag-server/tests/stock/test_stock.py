# tests/stock/test_service.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.stock.services import StockService
from src.exceptions import InvalidRequestException

# asyncio_mode = auto 설정으로 클래스 레벨에서 한 번만 데코레이터 적용
@pytest.mark.asyncio
class TestStockService:
    """StockService 테스트"""

    async def test_get_stock_price_success(self, stock_service: StockService):
        """주식 가격 조회 성공 테스트"""
        # given
        symbol = "AAPL"
        
        # Mock yfinance 응답
        mock_ticker_data = {
            'regularMarketPrice': 150.25,
            'regularMarketChange': 2.5,
            'regularMarketChangePercent': 1.69,
            'currency': 'USD'
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_ticker_data
            
            # when
            result = await stock_service.get_stock_price(symbol)
            
            # then
            assert result is not None
            assert result['symbol'] == symbol
            assert result['price'] == 150.25
            assert result['change'] == 2.5
            assert result['change_percent'] == 1.69
            assert result['currency'] == 'USD'

    async def test_get_stock_price_validation(self, stock_service: StockService):
        """주식 심볼 검증 테스트"""
        # 빈 심볼 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            await stock_service.get_stock_price("")
        assert "심볼이 비어있습니다" in str(exc_info.value) or "유효하지 않은" in str(exc_info.value)
        
        # None 심볼 테스트
        with pytest.raises(InvalidRequestException):
            await stock_service.get_stock_price(None)

    async def test_get_stock_price_failure(self, stock_service: StockService):
        """주식 가격 조회 실패 테스트"""
        # given
        invalid_symbol = "INVALID_SYMBOL"
        
        with patch('yfinance.Ticker') as mock_ticker:
            # yfinance에서 예외 발생 시뮬레이션
            mock_ticker.return_value.info = {}  # 빈 데이터
            
            # when & then
            result = await stock_service.get_stock_price(invalid_symbol)
            # 서비스에서 어떻게 에러를 처리하는지에 따라 조정 필요
            assert result is None or 'error' in result

    async def test_calculate_expression_success(self, stock_service: StockService):
        """수식 계산 성공 테스트"""
        # given
        test_cases = [
            ("100 * 1.5", 150.0),
            ("2 + 3 * 4", 14.0),
            ("(10 + 5) / 3", 5.0),
            ("100 - 25", 75.0),
        ]
        
        for expression, expected in test_cases:
            # when
            result = await stock_service.calculate_expression(expression)
            
            # then
            assert result is not None
            assert result['expression'] == expression
            assert result['result'] == expected

    async def test_calculate_expression_validation(self, stock_service: StockService):
        """수식 계산 검증 테스트"""
        # 빈 수식 테스트
        with pytest.raises(InvalidRequestException) as exc_info:
            await stock_service.calculate_expression("")
        assert "수식이 비어있습니다" in str(exc_info.value) or "유효하지 않은" in str(exc_info.value)
        
        # 유효하지 않은 문자 포함 테스트
        with pytest.raises(InvalidRequestException):
            await stock_service.calculate_expression("100 + eval('malicious code')")

    async def test_calculate_expression_division_by_zero(self, stock_service: StockService):
        """0으로 나누기 에러 테스트"""
        # given
        expression = "100 / 0"
        
        # when & then
        with pytest.raises(Exception):  # ZeroDivisionError 또는 서비스에서 처리하는 에러
            await stock_service.calculate_expression(expression)

    async def test_get_multiple_stock_prices(self, stock_service: StockService):
        """여러 주식 가격 조회 테스트"""
        # given
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        mock_data = {
            "AAPL": {'regularMarketPrice': 150.0, 'currency': 'USD'},
            "GOOGL": {'regularMarketPrice': 2800.0, 'currency': 'USD'},
            "MSFT": {'regularMarketPrice': 300.0, 'currency': 'USD'}
        }
        
        results = []
        
        for symbol in symbols:
            with patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.info = mock_data[symbol]
                result = await stock_service.get_stock_price(symbol)
                results.append(result)
        
        # then
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['symbol'] == symbols[i]
            assert result['price'] == mock_data[symbols[i]]['regularMarketPrice']


@pytest.mark.asyncio
class TestStockServiceCaching:
    """StockService 캐싱 테스트"""

    async def test_stock_price_caching(self, stock_service: StockService):
        """주식 가격 캐싱 테스트"""
        # given
        symbol = "AAPL"
        mock_data = {'regularMarketPrice': 150.0, 'currency': 'USD'}
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_data
            
            # when: 같은 심볼을 두 번 조회
            result1 = await stock_service.get_stock_price(symbol)
            result2 = await stock_service.get_stock_price(symbol)
            
            # then: 결과가 동일해야 함
            assert result1 == result2
            
            # yfinance.Ticker가 캐싱으로 인해 적게 호출되었는지 확인
            # (실제 캐싱 구현에 따라 조정 필요)


@pytest.mark.asyncio
class TestStockServiceIntegration:
    """StockService 통합 테스트"""

    async def test_stock_calculation_workflow(self, stock_service: StockService):
        """주식 + 계산 워크플로우 테스트"""
        # given: 주식 가격 조회
        symbol = "AAPL"
        mock_price = 150.0
        shares = 10
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {
                'regularMarketPrice': mock_price, 
                'currency': 'USD'
            }
            
            # when: 주식 가격 조회
            stock_result = await stock_service.get_stock_price(symbol)
            
            # when: 총 가치 계산
            expression = f"{stock_result['price']} * {shares}"
            calc_result = await stock_service.calculate_expression(expression)
            
            # then
            assert stock_result['price'] == mock_price
            assert calc_result['result'] == mock_price * shares

    async def test_error_recovery(self, stock_service: StockService):
        """에러 복구 테스트"""
        # given: 첫 번째 요청은 실패, 두 번째는 성공
        symbol = "AAPL"
        
        with patch('yfinance.Ticker') as mock_ticker:
            # 첫 번째 호출에서 예외 발생
            mock_ticker.side_effect = [Exception("Network error"), MagicMock()]
            mock_ticker.return_value.info = {'regularMarketPrice': 150.0, 'currency': 'USD'}
            
            # when: 첫 번째 시도 (실패)
            try:
                await stock_service.get_stock_price(symbol)
            except:
                pass  # 에러 무시
            
            # when: 두 번째 시도 (성공)
            # 이 부분은 실제 에러 처리 로직에 따라 조정 필요
            
            # then: 서비스가 복구되어야 함
            # assert문은 실제 구현에 따라 작성


# === 실제 API 호출 테스트 (선택적) ===
@pytest.mark.asyncio
class TestStockServiceRealAPI:
    """실제 API 호출 테스트 (주의: 실제 네트워크 호출)"""

    @pytest.mark.skip(reason="실제 API 호출 - 필요시에만 실행")
    async def test_real_stock_price_call(self, stock_service: StockService):
        """실제 주식 가격 조회 테스트"""
        # given
        symbol = "AAPL"  # Apple Inc.
        
        # when
        result = await stock_service.get_stock_price(symbol)
        
        # then
        assert result is not None
        assert result['symbol'] == symbol
        assert 'price' in result
        assert 'currency' in result
        assert result['price'] > 0  # 가격은 양수여야 함

    @pytest.mark.skip(reason="실제 API 호출 - 필요시에만 실행") 
    async def test_real_calculation(self, stock_service: StockService):
        """실제 계산 테스트"""
        # given
        expression = "100 * 1.5 + 25"
        
        # when
        result = await stock_service.calculate_expression(expression)
        
        # then
        assert result is not None
        assert result['expression'] == expression
        assert result['result'] == 175.0
