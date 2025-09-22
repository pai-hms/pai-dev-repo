
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

# 완전 재빌드
docker-compose down
docker-compose build --no-cache
docker-compose up

# 종료 후 재실행
docker-compose down
docker-compose up

# streamlit app 재실행
docker-compose restart streamlit app
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

### 기본 질문하기
```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "2023년 포항시의 인구는?"}'
```

### 메모리 지원 질문하기 - AsyncPostgresSaver 기반
```bash
# 첫 번째 질문
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "안녕하세요! 저는 홍민식입니다.", "session_id": "my_session"}'

# 연속 질문 (메모리 기능 확인)
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "제 이름이 뭐라고 했죠?", "session_id": "my_session"}'
```

### 메모리 기능 테스트
```bash
# Docker 환경에서 메모리 테스트 실행
docker-compose --profile test run --rm test-memory

# 또는 API로 직접 테스트
curl -X GET "http://localhost:8000/api/agent/test-memory"

# 세션 기록 조회
curl -X GET "http://localhost:8000/api/agent/session/my_session/history"

# 세션 삭제
curl -X DELETE "http://localhost:8000/api/agent/session/my_session"
```

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

## 데이터베이스 접근

```bash
# PostgreSQL 접속
docker-compose exec postgres psql -U postgres -d pai_sql_agent

# 테이블 목록 확인
\dt

# 데이터 확인
SELECT COUNT(*) FROM population_stats;
SELECT * FROM crawl_logs ORDER BY created_at DESC LIMIT 10;

# 크롤링 실행
docker-compose exec app python -m src.database.init_data
```

## 빠른 데이터 확인 명령어

```bash
# 한 줄로 데이터 개수 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT COUNT(*) FROM population_stats;"

# 연도별 데이터 현황
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT year, COUNT(*) FROM population_stats GROUP BY year ORDER BY year;"

# 최근 크롤링 로그 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT api_endpoint, year, status, created_at FROM crawl_logs ORDER BY created_at DESC LIMIT 5;"

# 실제 지역명들 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT DISTINCT adm_nm FROM population_stats ORDER BY adm_nm;"

# 특정 지역 데이터 확인 (예: 경기도)
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT year, adm_nm, tot_ppltn FROM population_stats WHERE adm_nm LIKE '%경기도%' ORDER BY year;"

# 현재 저장된 데이터의 행정구역 코드 길이 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT adm_cd, adm_nm, LENGTH(adm_cd) as code_length FROM population_stats WHERE year = 2023 ORDER BY adm_cd LIMIT 10;"

# 테이블 구조 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "\d population_stats"

# 샘플 데이터 확인
docker-compose exec postgres psql -U postgres -d pai_sql_agent -c "SELECT adm_cd, adm_nm, tot_ppltn FROM population_stats WHERE year = 2023 ORDER BY adm_cd;"

```