
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
python -m pytest tests/chat_session/test_chat_session.py -v
python -m pytest tests/chatbot/test_domains.py -v
python -m pytest tests/chatbot/test_repository.py -v
python -m pytest tests/chatbot/test_chatbot.py -v
```

### 환경변수 방법 (import 오류 시)
```bash
PYTHONPATH=$PWD python -m pytest tests/ -v
```
