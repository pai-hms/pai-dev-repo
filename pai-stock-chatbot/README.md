# PAI Stock Chatbot

주식 가격 조회 및 계산을 도와주는 AI 챗봇입니다.

## 개발 환경 설정

### uv 설치
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는 Homebrew 사용 (macOS)
brew install uv
```

### 백엔드 설정
```bash
cd rag-server
uv sync --dev
```

## 실행

### 백엔드 서버 실행
```bash
uv run uvicorn webapp.main:app --reload
```

### 프론트엔드 실행
```bash
cd rag-streamlit
uv run streamlit run streamlit_app.py
```

## 테스트 실행
```bash
cd rag-server
uv run pytest
```
