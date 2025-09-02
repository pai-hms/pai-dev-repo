# PAI Stock Chatbot

주식 가격 조회 및 계산을 도와주는 AI 챗봇입니다.


# 의존성 설치
pip install -r requirements.txt
```

### 환경변수 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 서버 실행
```bash
# FastAPI 서버 실행 (터미널 1)
uvicorn app.main:app --reload

# Streamlit UI 실행 (터미널 2)
streamlit run app/ui_streamlit.py
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
```
