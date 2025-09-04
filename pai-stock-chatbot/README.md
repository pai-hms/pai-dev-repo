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

### 프로젝트 설정
```bash
# 의존성 lock 파일 생성 (처음 한 번만 또는 pyproject.toml 변경 시)
uv lock

# 가상환경 생성 및 의존성 설치
uv sync

# 개발 의존성 포함하여 설치
uv sync --dev
```

## 환경변수 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

## 실행

### 가상환경 활성화 방법: uv run 사용
```bash
# 프로젝트 루트에서
cd rag-server
uv run uvicorn webapp.main:app --reload

# 프로젝트 루트에서
cd rag-streamlit-app
uv run streamlit run streamlit_app.py
```

## 테스트 실행
```bash

# uv run 사용
uv run pytest

# 상세 출력
uv run pytest -v

# 또는 가상환경 활성화 후
source .venv/bin/activate
pytest -v
```
