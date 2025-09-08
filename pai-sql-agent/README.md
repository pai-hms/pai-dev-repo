# PAI SQL Agent

지방자치단체 예산 및 종합 도시 데이터 분석을 위한 고도화된 SQL Agent 시스템입니다. LangGraph를 기반으로 구축되었으며, 지방자치단체 예산 데이터와 SGIS의 포괄적인 센서스 통계를 활용하여 심층적인 도시 분석을 제공합니다. (예시: 2023년 포항시 데이터)

## 설치 및 실행

### Docker 실행 (권장)

```bash
# 1. 환경 변수 설정
cp env.example .env
# .env 파일에서 OPENAI_API_KEY 설정 필수!

# 2. Docker로 실행
./docker-start.sh

# 또는 직접 실행
docker-compose up --build
```

### 로컬 실행

```bash
# 1. 의존성 설치
poetry install

# 2. PostgreSQL 시작
docker run --name postgres-pai \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=pai_sql_agent \
  -p 5432:5432 -d postgres:15

# 3. 데이터베이스 초기화
python src/database/init_data.py

# 4. 서버 시작
python webapp/main.py
```

##데이터베이스 스키마

### 예산 데이터
- **budget_categories**: 예산 분류 체계 (계층구조)
- **budget_items**: 지방자치단체 예산 항목 (예시: 2023년 포항시 150억+ 규모)

### 인구통계 데이터
- **population_data**: 기본 인구 센서스 (연령대별, 성별)
- **household_data**: 가구 통계 (1인가구, 다인가구, 평균가구원수)
- **household_member_data**: 가구구성원 상세 정보

### 주거 데이터
- **housing_data**: 주택 유형 및 소유형태 (단독주택, 아파트, 자가, 전세)

### 경제 데이터
- **company_data**: 사업체 통계 (제조업, 서비스업, 건설업 등)
- **industry_data**: 산업분류별 사업체 및 종사자 수

### 1차 산업 데이터
- **agricultural_household_data**: 농업 가구 (전업농, 겸업농, 경작면적)
- **forestry_household_data**: 임업 가구 (임업인구, 산림면적)
- **fishery_household_data**: 어업 가구 (어선수, 양식장수)

### 시스템 데이터
- **query_history**: 쿼리 실행 이력 및 학습 데이터
- **agent_checkpoints**: Agent 상태 영속성 관리

## API 엔드포인트

### Agent API

- `POST /agent/ask`: 질문하기
- `POST /agent/stream`: SSE 스트리밍
- `POST /agent/stream-json`: JSON 라인 스트리밍

### Data API

- `GET /data/budget/categories`: 예산 분류 조회
- `GET /data/budget/items`: 예산 항목 조회
- `GET /data/population`: 인구 데이터 조회
- `GET /data/queries/history`: 쿼리 이력 조회

### 시스템 API

- `GET /health`: 헬스 체크
- `GET /`: 서비스 정보

## 💡 사용 예시

### 1. 기본 질문

```bash
curl -X POST "http://localhost:8000/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "2023년 교육 예산은 얼마인가요?"
  }'
```

### 2. 스트리밍 응답

```bash
curl -X POST "http://localhost:8000/agent/stream-json" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "인구 대비 복지 예산 비율을 분석해주세요"
  }'
```

### 3. 분석 질문 예시

```bash
# 교육 예산 분석
curl -X POST "http://localhost:8000/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "교육 예산이 학령인구 대비 적절한가요?"}'

# 복지 예산 분석
curl -X POST "http://localhost:8000/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "1인 가구 증가와 주거 예산의 관계를 분석해주세요"}'
```

## 🔧 유용한 명령어

```bash
# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f

# 데이터베이스 접속
docker-compose exec postgres psql -U postgres -d pai_sql_agent

# 완전 정리 (데이터 삭제)
docker-compose down -v
```

## 모니터링

- **헬스 체크**: http://localhost:8000/health
- **API 문서**: http://localhost:8000/docs
- **쿼리 이력**: http://localhost:8000/data/queries/history
