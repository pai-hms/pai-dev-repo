# PAI Web Agent

OpenAI와 Tavily API를 활용한 LangGraph 기반 Supervised Agent입니다. React 패턴을 사용하여 사용자 질문에 대해 추론하고 실시간 웹 검색을 통해 정확한 답변을 제공합니다.

## 주요 기능

- **🏛️ 공공기관 정보 특화**: *.go.kr, *.or.kr 도메인 우선 검색
- **🤖 전문 분야별 AI**: 정부기관, 공공기관, 통계, 정책 전문 프롬프트
- **LangGraph 기반 Supervised Agent**: React 패턴으로 질문 분석 및 도구 활용
- **OpenAI GPT 모델 통합**: 자연어 이해 및 응답 생성
- **Tavily 웹 검색**: 실시간 정보 검색 및 사실 확인
- **🌐 도메인 필터링**: 특정 사이트만 검색하거나 제외 가능
- **대화 기록 관리**: 메모리 기반 컨텍스트 유지
- **비동기 처리 지원**: 효율적인 응답 처리
- **스트리밍 응답**: 실시간 처리 과정 확인

## 설치 및 설정

### 1. uv를 사용한 의존성 설치

```bash
# uv 설치 (아직 설치하지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 의존성 설치
uv sync
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 API 키를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일에 다음 내용을 추가:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Tavily API Key
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. API 키 발급

- **OpenAI API**: [OpenAI Platform](https://platform.openai.com/api-keys)에서 발급
- **Tavily API**: [Tavily](https://tavily.com/)에서 계정 생성 후 발급 (월 1,000회 무료)

## 사용법

### 1. 대화형 실행

```bash
uv run python agent.py
```

### 2. Streamlit 웹 인터페이스

```bash
# 메인 웹 인터페이스 (모든 기능 포함)
uv run streamlit run app.py

# 실행 스크립트 사용
uv run python run_streamlit.py        # 메인 앱
```

## 프로젝트 구조

```
pai-web-agent/
├── agent.py                # 메인 에이전트 구현 (그래프 기반)
├── nodes.py                # LangGraph 커스텀 노드 정의
├── graph.py                # LangGraph 그래프 구조 및 상태 관리
├── tools.py                # Tavily 검색 도구
├── prompts.py              # 프롬프트 관리 모듈
├── app.py                  # 메인 Streamlit 웹 인터페이스
├── app_simple.py           # 간단한 Streamlit 인터페이스
├── test_streamlit.py       # Streamlit 테스트 스크립트
├── run_streamlit.py        # Streamlit 실행 스크립트
├── pyproject.toml          # uv 의존성 관리
├── uv.lock                 # 의존성 잠금 파일
├── README.md               # 프로젝트 문서
└── STREAMLIT_GUIDE.md      # Streamlit 사용 가이드
```

## LangGraph 아키텍처

### 🔄 워크플로우
```
사용자 질문 → [분석] → [검색] → [응답] → 최종 답변
```

### 📋 노드 구조

#### QueryAnalysisNode (분석)
- 사용자 질문 분석 및 검색 필요성 판단
- 질문 타입 분류 (factual, statistics, policy 등)
- 도메인 제안 및 신뢰도 평가

#### SearchNode (검색)  
- Tavily API를 통한 웹 검색
- 도메인 필터링 및 검색 깊이 조절
- 검색 결과 수집 및 정리

#### ResponseGenerationNode (응답)
- 검색 결과 기반 최종 답변 생성
- 출처 명시 및 구조화된 응답
- 오류 처리 및 한계 명시

### 🏗️ 주요 클래스

#### SupervisedAgent
- `process_query(query, thread_id)`: 동기 질문 처리 (그래프 기반)
- `process_query_async(query, thread_id)`: 비동기 질문 처리
- `stream_response(query, thread_id, stream_mode)`: 스트리밍 응답
- `get_graph_info()`: 그래프 구조 정보 조회

#### PublicInfoGraph
- `invoke(query, search_settings)`: 동기 그래프 실행
- `ainvoke(query, search_settings)`: 비동기 그래프 실행  
- `stream(query, search_settings, stream_mode)`: 스트리밍 실행

#### TavilySearchTool
- `search(query, include_domains, exclude_domains)`: 웹 검색 실행
- 도메인 필터링 및 검색 설정 지원

## 개발 환경

### 코드 포맷팅

```bash
uv run black .
```

### 린팅

```bash
uv run flake8 .
```

### 테스트 (개발 의존성 설치 후)

```bash
uv sync --dev
uv run pytest
```

## 전문 분야별 프롬프트

### 🏛️ 정부기관 (government)
- 정부 정책 및 행정 정보 전문
- 우선 검색: *.go.kr, korea.kr, president.go.kr

### 📊 공공기관 (public_institution)  
- 공기업 및 공공서비스 전문
- 우선 검색: *.or.kr, bok.or.kr, nhis.or.kr

### 📈 통계 (statistics)
- 국가통계 및 데이터 분석 전문
- 우선 검색: kostat.go.kr, kosis.kr

### 📋 정책 (policy)
- 정부 정책 및 법령 정보 전문
- 우선 검색: 각 부처 사이트, 법제처

## 예제 질문

### 공공기관 정보
- "2025년 대한민국 예산 규모는?"
- "최근 통계청 발표 주요 지표는?"
- "대구광역시 2025년 재정 현황은?"
- "정부 정책 최신 동향은?"
- "공공기관 채용 정보는?"
- "국가통계포털 최신 데이터는?"

### 일반 정보
- "2025년 노벨물리학상 수상자는 누구인가요?"
- "최신 ChatGPT 업데이트 내용을 알려주세요"
