# PAI Stock Chatbot

주식 가격 조회 및 계산을 도와주는 AI 챗봇입니다.

## 의존성 설치
```bash
pip install -r requirements.txt
```

## 환경변수 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

## 테스트 실행
```bash
# 모든 테스트
pytest

# 상세 출력
pytest -v

# 특정 테스트
pytest tests/test_agent.py -v
pytest tests/test_multiSession.py -v

# 노드 단계별 스트리밍 테스트
python streaming.py
```
