
## 빠른 시작

### 1. 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# 필수 환경 변수 설정
OPENAI_API_KEY=your_openai_api_key
SGIS_API_KEY=your_sgis_access_key
SGIS_SECRET_KEY=your_sgis_secret_key
```

### 2. Docker 실행

```bash
# PostgreSQL과 애플리케이션 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build
```

### 3. 로컬 개발 환경

```bash
# uv 설치 (권장)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv pip install -e .

# PostgreSQL 실행 (Docker)
docker-compose up -d postgres

# FastAPI 서버 실행
uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload

# Streamlit 앱 실행 (별도 터미널)
streamlit run webapp/streamlit_app.py --server.port 8501
```

## 서비스 접근

- FastAPI 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Streamlit 앱: http://localhost:8501
- PostgreSQL: localhost:5432

## API 사용법

### 질문하기
```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "2023년 포항시의 인구는?"}'
```

## 주요 기능

- 자연어 질문을 SQL 쿼리로 변환
- 실시간 스트리밍 응답
- PostgreSQL 기반 세션 관리
- SGIS API 통계 데이터 크롤링
- FastAPI 기반 REST API
- Streamlit 웹 인터페이스

## 기술 스택

- AI Framework: LangGraph, LangChain
- LLM: OpenAI GPT-4
- Database: PostgreSQL
- Web Framework: FastAPI, Streamlit
- Package Manager: uv
- Containerization: Docker, Docker Compose

## 환경 변수

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# SGIS API
SGIS_API_KEY=your_sgis_access_key
SGIS_SECRET_KEY=your_sgis_secret_key

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/pai_sql_agent

# Application
LOG_LEVEL=INFO
DEBUG=false
```

## 문제 해결

### 데이터베이스 연결 오류
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 로그 확인
docker-compose logs postgres
```

### 볼륨 정리 (데이터베이스 초기화)
```bash
docker-compose down -v
docker volume prune -f
docker-compose up --build
```

### 의존성 재설치
```bash
# uv 사용
uv pip install --force-reinstall -e .

# 또는 Docker 캐시 없이 빌드
docker-compose build --no-cache
```

## 질문 예시

- 2023년 포항시의 인구는?
- 서울특별시에서 인구밀도가 가장 높은 구는?
- 경상북도 시군구별 2020년 대비 2023년 인구 증감률
- 전국에서 고령화지수가 가장 높은 지역 10곳
- 포항시 남구와 북구의 사업체 수 비교