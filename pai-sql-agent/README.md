# PAI SQL Agent

LangGraph 기반 한국 센서스 통계 데이터 SQL 에이전트

## 🎯 프로젝트 개요

이 프로젝트는 한국 통계청의 SGIS(통계지리정보서비스) API를 활용하여 센서스 통계 데이터를 수집하고, LangGraph 기반의 AI 에이전트를 통해 자연어 질문에 대한 SQL 쿼리를 생성하여 답변하는 시스템입니다.

## 🏗️ 시스템 아키텍처

```
사용자 질문 → LangGraph Agent → SQL Tool → PostgreSQL → 결과 반환
                ↓
            SGIS API ← 데이터 크롤링 ← PostgreSQL
```

## 📊 주요 기능

- **자연어 질문 처리**: "2023년 포항시의 인구는?" 같은 자연어 질문을 SQL로 변환
- **실시간 스트리밍**: 첫 토큰부터 빠른 응답 제공
- **영속적 세션 관리**: PostgreSQL 기반 체크포인터로 대화 상태 저장
- **다양한 통계 데이터**: 인구, 가구, 주택, 사업체, 농림어업 통계
- **웹 인터페이스**: Streamlit 기반 사용자 친화적 UI

## 🗄️ 데이터 구조

### 인구 통계 (2015-2023)
- 총인구, 평균나이, 인구밀도
- 성별/연령대별 인구
- 노령화지수, 부양비

### 가구/주택 통계 (2015-2023)
- 가구수, 평균 가구원수
- 주택 유형별 통계

### 사업체 통계 (2000-2023)
- 사업체수, 종사자수

### 농림어업 통계
- 농가, 임가, 어가 통계
- 가구원 상세 정보

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd pai-sql-agent

# 환경 변수 설정
cp env.example .env
# .env 파일에서 API 키 설정
```

### 2. Docker Compose 실행

```bash
# PostgreSQL과 애플리케이션 실행
docker-compose up -d

# 또는 개발 모드로 실행
docker-compose up --build
```

### 3. 로컬 개발 환경

```bash
# Poetry 설치 및 의존성 설치
pip install poetry
poetry install

# PostgreSQL 실행 (Docker)
docker-compose up -d postgres

# 데이터베이스 마이그레이션
poetry run alembic upgrade head

# 데이터 초기화 (SGIS API 크롤링)
poetry run python -m src.database.init_data

# FastAPI 서버 실행
poetry run uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload

# Streamlit 앱 실행 (별도 터미널)
poetry run streamlit run webapp/streamlit_app.py --server.port 8501
```

## 🔧 환경 변수

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# SGIS API
SGIS_ACCESS_KEY=your_sgis_access_key
SGIS_SECRET_KEY=your_sgis_secret_key

# Database
DATABASE_URL=postgresql://pai_user:pai_password@localhost:5432/pai_sql_agent

# Application
LOG_LEVEL=INFO
DEBUG=false
```

## 📝 API 사용법

### 질문하기
```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "2023년 포항시의 인구는?"}'
```

### 스트리밍 응답
```bash
curl -X POST "http://localhost:8000/api/agent/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"question": "서울특별시 구별 인구 밀도 비교", "stream": true}'
```

## 🎨 Streamlit 웹앱

- **URL**: http://localhost:8501
- **기능**:
  - 대화형 채팅 인터페이스
  - 테이블 스키마 정보 조회
  - 행정구역 검색
  - 실행된 SQL 쿼리 확인
  - 시스템 상태 모니터링

## 📈 질문 예시

```
• 2023년 포항시의 인구는?
• 서울특별시에서 인구밀도가 가장 높은 구는?
• 경상북도 시군구별 2020년 대비 2023년 인구 증감률
• 전국에서 고령화지수가 가장 높은 지역 10곳
• 포항시 남구와 북구의 사업체 수 비교
• 2023년 전국 농가 수가 많은 시도 순위
```

## 🏛️ 아키텍처 설계 원칙

1. **KISS 원칙**: 가능한 가장 간단한 구조
2. **단방향 참조**: webapp → src 방향으로만 참조
3. **데이터와 로직 일체화**: 데이터와 관련 로직을 가까이 배치
4. **데이터 주권**: Repository가 데이터 제어권 담당
5. **Container 관리**: DI를 통한 의존관계 명세
6. **SLAP**: 코드 라인별 추상화 수준 통일
7. **선형원리**: 직선적 흐름으로 가독성 향상

## 🔍 프로젝트 구조

```
pai-sql-agent/
├── src/                    # 핵심 로직
│   ├── config/            # 설정 관리
│   ├── database/          # 데이터베이스 관련
│   ├── crawler/           # SGIS API 크롤링
│   ├── agent/             # LangGraph 에이전트
│   └── tools/             # SQL 도구
├── webapp/                # 웹 애플리케이션
│   ├── routers/           # FastAPI 라우터
│   ├── main.py           # FastAPI 앱
│   ├── models.py         # Pydantic 모델
│   └── streamlit_app.py  # Streamlit 앱
├── alembic/              # 데이터베이스 마이그레이션
├── tests/                # 테스트
├── docker-compose.yml    # Docker 구성
├── Dockerfile           # 컨테이너 이미지
└── pyproject.toml       # 프로젝트 설정
```

## 🛠️ 기술 스택

- **AI Framework**: LangGraph, LangChain
- **LLM**: OpenAI GPT-4
- **Database**: PostgreSQL
- **Web Framework**: FastAPI, Streamlit
- **Data Processing**: asyncpg, SQLAlchemy
- **API Integration**: SGIS API (통계청)
- **Containerization**: Docker, Docker Compose

## 📊 성능 특징

- **첫 토큰 지연 최소화**: 스트리밍 모드로 즉시 응답 시작
- **세션 영속성**: PostgreSQL 체크포인터로 대화 상태 유지
- **비동기 처리**: 전체 파이프라인 비동기 구현
- **효율적 쿼리**: 인덱스 최적화 및 쿼리 검증

## 🔒 보안

- SQL 인젝션 방지: 쿼리 검증 및 허용 테이블 제한
- READ-ONLY 권한: SELECT 쿼리만 허용
- API 키 관리: 환경 변수를 통한 안전한 키 관리

## 🚨 문제 해결

### 데이터베이스 연결 오류
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 로그 확인
docker-compose logs postgres
```

### SGIS API 오류
- API 키 확인
- 요청 제한 확인 (하루 1000건)
- 네트워크 연결 상태 확인

### 메모리 부족
- Docker 메모리 할당량 증가
- 대용량 쿼리 결과 제한 설정

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 문의

프로젝트 관련 문의는 이슈를 통해 남겨주세요.
