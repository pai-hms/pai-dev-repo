
## 실행 방법

### 기본 실행
```bash
cd rag-server

# 전체 테스트
python -m pytest tests/ -v

# 특정 모듈
python -m pytest tests/chatbot/ -v

# 특정 파일 테스트
python -m pytest tests/agent/test_agent.py -v
```
