# 테스트 가이드

이 디렉토리는 PAI Stock Chatbot 프로젝트의 테스트 코드를 포함합니다.

## 📁 테스트 구조

```
tests/
├── conftest.py                # 전역 테스트 설정 및 fixtures
├── pytest.ini                # pytest 설정
├── README.md                  # 이 파일
├── chat_session/              # ChatSession 관련 테스트
│   ├── test_domains.py        # 도메인 객체 테스트
│   ├── test_repository.py     # Repository 테스트
│   └── test_service.py        # Service 테스트
├── chatbot/                   # Chatbot 관련 테스트
│   └── test_service.py        # ChatbotService 테스트
├── stock/                     # Stock 관련 테스트
│   └── test_service.py        # StockService 테스트
└── agent/                     # Agent 관련 테스트
    └── test_service.py        # AgentService 테스트
```

## 🎯 테스트 카테고리

### 1. 단위 테스트 (Unit Tests)
- **목적**: 개별 함수/메서드의 정확성 검증
- **범위**: Repository, Service, Domain 객체
- **특징**: Mock 사용, 빠른 실행

### 2. 통합 테스트 (Integration Tests)  
- **목적**: 모듈 간 상호작용 검증
- **범위**: Service 간 협력, 전체 워크플로우
- **특징**: 실제 객체 사용

### 3. 에러 처리 테스트
- **목적**: 예외 상황 처리 검증
- **범위**: 입력 검증, 네트워크 오류, 데이터 오류
- **특징**: Exception 발생 시나리오

## 🚀 테스트 실행 방법

### 전체 테스트 실행
```bash
cd rag-server
pytest
```

### 특정 모듈 테스트
```bash
# ChatSession 관련 테스트만
pytest tests/chat_session/

# ChatbotService 테스트만  
pytest tests/chatbot/test_service.py

# 특정 테스트 클래스만
pytest tests/chat_session/test_service.py::TestChatSessionService

# 특정 테스트 함수만
pytest tests/chat_session/test_service.py::TestChatSessionService::test_start_new_session
```

### 마커 기반 실행
```bash
# 단위 테스트만
pytest -m unit

# 통합 테스트만  
pytest -m integration

# 느린 테스트 제외
pytest -m "not slow"

# 스킵된 테스트 제외
pytest -m "not skip"
```

### 상세한 출력
```bash
# 자세한 정보
pytest -v

# 실패한 테스트만 재실행
pytest --lf

# 커버리지 포함 (pytest-cov 설치 필요)
pytest --cov=src --cov-report=html
```

## 📋 테스트 작성 가이드

### 1. **네이밍 규칙**
```python
# 파일명: test_{모듈명}.py
# 클래스명: Test{클래스명}  
# 함수명: test_{테스트내용}_with_{조건} 또는 test_{테스트내용}_{결과}

def test_start_new_session_success(self):
def test_get_stock_price_with_invalid_symbol(self):
def test_stream_response_raises_exception(self):
```

### 2. **테스트 구조 (AAA 패턴)**
```python
def test_example(self):
    # given: 테스트 준비
    session_id = "test_session"
    message = "테스트 메시지"
    
    # when: 실제 실행
    result = service.process(session_id, message)
    
    # then: 검증
    assert result is not None
    assert result.success is True
```

### 3. **Mock 사용 예시**
```python
@patch('src.external.api_client')
def test_with_mock(self, mock_api):
    # Mock 설정
    mock_api.return_value = {"status": "success"}
    
    # 테스트 실행
    result = service.call_external_api()
    
    # Mock 호출 검증
    mock_api.assert_called_once()
    assert result["status"] == "success"
```

### 4. **비동기 테스트** (최적화됨!)
```python
# ✅ 효율적 방식: 클래스 레벨에서 한 번만 선언
@pytest.mark.asyncio
class TestAsyncService:
    async def test_async_function(self):  # 개별 데코레이터 불필요
        result = await async_service.process()
        assert result is not None
    
    async def test_another_async_function(self):  # 개별 데코레이터 불필요
        result = await async_service.another_process()
        assert result is not None

# ❌ 비효율적 방식: 매번 데코레이터 반복
class TestAsyncServiceOld:
    @pytest.mark.asyncio  # 매번 반복 필요
    async def test_async_function(self):
        ...
```

### 5. **예외 테스트**
```python
def test_invalid_input_raises_exception(self):
    with pytest.raises(InvalidRequestException) as exc_info:
        service.process_invalid_input("")
    
    assert "입력값이 유효하지 않습니다" in str(exc_info.value)
```

## 🔧 Fixture 활용

### conftest.py에서 제공하는 주요 Fixtures:
- `chat_session_service`: ChatSessionService 인스턴스
- `chatbot_service`: ChatbotService 인스턴스  
- `stock_service`: StockService 인스턴스
- `sample_chatbot_config`: 샘플 챗봇 설정
- `sample_chat_session`: 샘플 채팅 세션
- `mock_agent_executor`: Mock Agent Executor

### 사용 예시:
```python
def test_with_fixture(self, chat_session_service, sample_chat_session):
    # Fixture 자동 주입
    result = chat_session_service.get_session(sample_chat_session.session_id)
    assert result is not None
```

## ⚡ 성능 테스트

### 대량 데이터 처리 테스트
```python
def test_large_scale_processing(self):
    # 1000개 세션 생성 테스트
    for i in range(1000):
        session = repository.create_session(f"session_{i}")
        assert session is not None
```

### 동시성 테스트 (필요시)
```python
import asyncio

async def test_concurrent_processing(self):
    tasks = [service.process(f"message_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
```

## 🎛️ 환경별 테스트

### 개발 환경
```bash
pytest  # 전체 테스트
```

### CI/CD 환경
```bash
pytest -m "not slow" --tb=short  # 빠른 테스트만
```

### 배포 전 검증
```bash
pytest -m integration  # 통합 테스트
```

## 🐛 디버깅 팁

### 1. **실패한 테스트 디버깅**
```bash
# 실패 시 즉시 중단
pytest -x

# 상세한 에러 메시지
pytest --tb=long

# PDB 디버거 사용
pytest --pdb
```

### 2. **로그 확인**
```bash
# 로그 출력 활성화
pytest -s --log-cli-level=DEBUG
```

### 3. **특정 테스트만 반복 실행**
```bash
# 실패할 때까지 반복
pytest --maxfail=1 -x tests/specific_test.py
```

## 📊 테스트 커버리지

### 커버리지 측정
```bash
pip install pytest-cov
pytest --cov=src --cov-report=html
```

### 커버리지 목표
- **최소 커버리지**: 80%
- **중요 모듈**: 90% 이상
- **신규 코드**: 100%

## 🔒 보안 테스트

### 입력 검증 테스트
```python
def test_sql_injection_prevention(self):
    malicious_input = "'; DROP TABLE users; --"
    with pytest.raises(InvalidRequestException):
        service.process(malicious_input)
```

### 인증/인가 테스트
```python
def test_unauthorized_access(self):
    with pytest.raises(PermissionDeniedException):
        service.access_protected_resource(invalid_token)
```

이 가이드를 따라 일관성 있고 효과적인 테스트를 작성하세요! 🚀
