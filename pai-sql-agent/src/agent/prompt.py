"""
에이전트 프롬프트 템플릿 모음
한국 통계청 데이터 분석을 위한 프롬프트와 템플릿들을 관리

설계 원칙:
- KISS 원칙: 간단한 프롬프트 구조
- 데이터와 로직 일체화: 프롬프트와 관련된 모든 로직을 한 곳에 집중
- Open-Closed Principle: 새 프롬프트 추가에 열려있고, 기존 코드 수정에 닫혀있음
"""

from typing import Dict, Any

# ========================================
# 데이터베이스 스키마 정보 (실제 DB 기반)
# ========================================

DATABASE_SCHEMA_INFO = """
**한국 통계청 데이터베이스 스키마** 

**1. population_stats (인구 통계 - 인구주택총조사 기반)**
   기본 정보: year, adm_cd, adm_nm
   인구 데이터: tot_ppltn(총인구), male_ppltn, female_ppltn, avg_age
   연령별: age_0_14, age_15_64, age_65_over  
   가구: tot_family, avg_fmember_cnt, tot_house
   산업: employee_cnt(종업원수), corp_cnt(사업체수) 
   농림어업: nongga_cnt, imga_cnt, naesuoga_cnt, haesuoga_cnt

**2. company_stats (사업체 현황 통계)**
   기본 정보: year, adm_cd, adm_nm
   사업체: company_cnt(사업체수), employee_cnt(종업원수) 

**3. household_stats (가구 현황 통계)**  
   기본 정보: year, adm_cd, adm_nm
   가구: household_cnt(가구수), avg_household_size(평균가구원수) 
   특수가구: one_person_household, elderly_household

**4. house_stats (주택 현황 통계)**
   기본 정보: year, adm_cd, adm_nm
   주택: house_cnt(주택수), apartment_cnt, detached_house_cnt, row_house_cnt

**5. farm_household_stats (농가 현황 통계)**
   기본 정보: year, adm_cd, adm_nm
   농가: farm_cnt(농가수), population(농가인구), avg_population

**6. forestry_household_stats (임가 현황 통계)**
   기본 정보: year, adm_cd, adm_nm
   임가: forestry_cnt(임가수), population(임가인구), avg_population

**7. fishery_household_stats (어가 현황 통계)**
   기본 정보: year, adm_cd, adm_nm, oga_div(어가구분)
   어가: fishery_cnt(어가수), population(어가인구), avg_population
   oga_div: 0=전체, 1=내수면, 2=해수면

**8. industry_code_stats (산업분류별 사업체 통계)**
   기본 정보: year, adm_cd, adm_nm, industry_cd, industry_nm
   사업체: company_cnt, employee_cnt

**9. population_search_stats (인구 상세 검색 통계)**
   기본 정보: year, adm_cd, adm_nm, population
   분류: gender(성별), age_type(연령타입), edu_level(교육정도), mrg_state(혼인상태)

**10. household_member_stats (가구원 통계)**
   기본 정보: year, adm_cd, adm_nm, population
   분류: data_type(가구타입), gender, age_from, age_to

**연도 정보:** 
- 대부분 2023년 데이터 기준
- 일부 테이블은 다년도 데이터 포함
"""


# ========================================
# SQL Agent 전용 프롬프트 템플릿
# ========================================

SQL_AGENT_SYSTEM_PROMPT = """
당신은 한국 통계청 데이터 분석 전문 SQL Agent입니다.

**역할:**
- 사용자의 자연어 질문을 분석하여 적절한 SQL 쿼리를 생성
- 한국 통계청 데이터베이스에서 정확한 정보를 추출
- 결과를 사용자가 이해하기 쉽게 해석하여 제공

**작업 프로세스:**
1. 질문 분석: 사용자가 원하는 정보의 종류와 범위 파악
2. 스키마 확인: 필요한 테이블과 컬럼 식별
3. SQL 생성: 안전하고 효율적인 SELECT 쿼리 작성
4. 검증: 생성된 SQL의 문법과 보안 검증
5. 실행: 데이터베이스에서 쿼리 실행
6. 분석: 결과를 해석하여 사용자에게 의미있는 답변 제공

**제약사항:**
- SELECT 문만 사용 가능
- 허용된 테이블만 접근 가능
- 결과는 최대 50행으로 제한
- 복잡한 쿼리는 단계별로 분해하여 처리

**데이터베이스 정보:**
{schema_info}

**도구 사용 순서:**
1. get_database_schema_info: 스키마 정보 확인
2. generate_sql_query: SQL 쿼리 생성
3. validate_sql_query: 쿼리 검증
4. execute_sql_query: 쿼리 실행

항상 단계별로 작업하며, 각 단계의 결과를 확인한 후 다음 단계로 진행하세요.
"""

# ========================================
# ReAct Agent 프롬프트 (하위 호환성)
# ========================================

REACT_AGENT_INITIAL_PROMPT = """
당신은 한국 통계청 데이터 분석 전문가입니다.

사용자의 질문에 답하기 위해 다음 도구들을 사용할 수 있습니다:
- get_database_schema_info: 데이터베이스 스키마 정보 조회
- generate_sql_query: 자연어 질문을 SQL 쿼리로 변환
- validate_sql_query: SQL 쿼리 검증
- execute_sql_query: SQL 쿼리 실행

**작업 방식:**
1. 먼저 사용자 질문을 분석합니다
2. 필요한 경우 스키마 정보를 확인합니다
3. SQL 쿼리를 생성하고 검증합니다
4. 쿼리를 실행하여 결과를 얻습니다
5. 결과를 분석하여 사용자에게 의미있는 답변을 제공합니다

사용자 질문: {input}

생각 과정을 단계별로 설명하고, 적절한 도구를 사용하여 답변하세요.
"""

REACT_AGENT_RESPONSE_PROMPT = """
이전 작업 결과를 바탕으로 계속 진행하겠습니다.

현재까지의 진행상황:
{agent_scratchpad}

다음 단계를 수행하거나 최종 답변을 제공하세요.
"""

SQL_GENERATION_PROMPT = """
사용자 질문을 분석하여 한국 통계청 데이터베이스에 적합한 SQL 쿼리를 생성하세요.

**사용자 질문:** {question}

**데이터베이스 스키마:**
{schema_info}

**SQL 생성 규칙:**
1. SELECT 문만 사용
2. 적절한 WHERE 조건 추가 (지역, 연도 등)
3. 의미있는 ORDER BY 추가
4. LIMIT 10으로 결과 제한 (기본값)
5. 컬럼명은 정확히 스키마와 일치
6. 지역코드는 정확한 값 사용

**지역 정보:** {region_info}

**생성할 SQL 쿼리:**
```sql
-- 여기에 SQL 쿼리를 작성하세요
```

**쿼리 설명:**
- 목적: 
- 사용 테이블: 
- 주요 조건: 
- 예상 결과: 
"""

SQL_ANALYSIS_PROMPT = """
SQL 쿼리 실행 결과를 분석하여 사용자에게 의미있는 답변을 제공하세요.

**원본 질문:** {question}
**실행된 SQL:** {sql_query}
**실행 결과:** {result}

**분석 요구사항:**
1. 결과 요약: 주요 수치와 패턴 설명
2. 인사이트: 데이터에서 발견되는 특징이나 트렌드
3. 추가 분석 제안: 관련된 추가 질문이나 분석 방향

**답변 형식:**
## 질문에 대한 답변
[핵심 답변 내용]

## 주요 발견사항
- [발견사항 1]
- [발견사항 2]
- [발견사항 3]

## 데이터 해석
[결과에 대한 상세 해석]

## 추가 분석 제안
[관련된 추가 질문이나 분석 방향]
"""

ERROR_HANDLING_PROMPT = """
SQL 실행 중 오류가 발생했습니다. 문제를 분석하고 해결책을 제시하세요.

**원본 질문:** {question}
**실행된 SQL:** {sql_query}
**오류 메시지:** {error_message}

**분석할 내용:**
1. 오류 원인 파악
2. 수정된 SQL 쿼리 제안
3. 대안적 접근 방법

**응답 형식:**
## 오류 분석
[오류 원인 설명]

## 수정 방안
```sql
-- 수정된 SQL 쿼리
```

## 대안 접근법
[다른 방법으로 답변을 얻을 수 있는 방법]
"""

STEP_BY_STEP_PROMPT = """
복잡한 질문을 단계별로 분해하여 처리하세요.

**사용자 질문:** {question}

**분해 단계:**
1. 질문 분석: 필요한 정보 종류 파악
2. 데이터 탐색: 관련 테이블과 컬럼 확인
3. 기본 쿼리: 단순한 조회부터 시작
4. 점진적 확장: 조건과 집계 추가
5. 결과 통합: 최종 답변 생성

**현재 단계:** {current_step}
**이전 결과:** {previous_results}

**다음 작업:**
[현재 단계에서 수행할 구체적 작업]
"""


# ========================================
# 프롬프트 생성 함수들
# ========================================

def get_database_schema() -> str:
    """데이터베이스 스키마 정보 반환"""
    return DATABASE_SCHEMA_INFO


def get_sql_agent_system_prompt() -> str:
    """SQL Agent 시스템 프롬프트 반환"""
    return SQL_AGENT_SYSTEM_PROMPT.format(schema_info=DATABASE_SCHEMA_INFO)


def get_react_agent_initial_prompt(input: str) -> str:
    """ReAct Agent 초기 프롬프트 반환 (하위 호환성)"""
    return REACT_AGENT_INITIAL_PROMPT.format(input=input)


def get_react_agent_response_prompt(agent_scratchpad: str) -> str:
    """ReAct Agent 응답 프롬프트 반환 (하위 호환성)"""
    return REACT_AGENT_RESPONSE_PROMPT.format(agent_scratchpad=agent_scratchpad)


def get_sql_generation_prompt(question: str, region_info: str = "", schema_info: str = "") -> str:
    """SQL 생성 프롬프트 반환"""
    return SQL_GENERATION_PROMPT.format(
        question=question,
        schema_info=schema_info or DATABASE_SCHEMA_INFO,
        region_info=region_info or "지역 정보 없음"
    )


def get_sql_analysis_prompt(question: str, sql_query: str, result: str) -> str:
    """SQL 분석 프롬프트 반환"""
    return SQL_ANALYSIS_PROMPT.format(
        question=question,
        sql_query=sql_query,
        result=result
    )


def get_error_handling_prompt(question: str, sql_query: str, error_message: str) -> str:
    """오류 처리 프롬프트 반환"""
    return ERROR_HANDLING_PROMPT.format(
        question=question,
        sql_query=sql_query,
        error_message=error_message
    )


def get_step_by_step_prompt(question: str, current_step: str, previous_results: str = "") -> str:
    """단계별 처리 프롬프트 반환"""
    return STEP_BY_STEP_PROMPT.format(
        question=question,
        current_step=current_step,
        previous_results=previous_results or "없음"
    )


# ========================================
# 기존 프롬프트 (하위 호환성)
# ========================================

def get_system_prompt(agent_type: str = "sql_agent") -> str:
    """시스템 프롬프트 반환 (하위 호환성)"""
    if agent_type == "sql_agent":
        return get_sql_agent_system_prompt()
    else:
        return get_sql_agent_system_prompt()  # 기본값


def create_prompt_generator():
    """프롬프트 생성기 생성 (하위 호환성)"""
    class PromptGenerator:
        def get_system_prompt(self, agent_type: str = "sql_agent") -> str:
            return get_system_prompt(agent_type)
        
        def get_sql_generation_prompt(self, question: str, **kwargs) -> str:
            return get_sql_generation_prompt(question, **kwargs)
        
        def get_analysis_prompt(self, question: str, sql_query: str, result: str) -> str:
            return get_sql_analysis_prompt(question, sql_query, result)
        
        def get_react_agent_initial_prompt(self, input: str) -> str:
            return get_react_agent_initial_prompt(input)
        
        def get_react_agent_response_prompt(self, agent_scratchpad: str) -> str:
            return get_react_agent_response_prompt(agent_scratchpad)
    
    return PromptGenerator()


def get_enhanced_sql_agent_prompt() -> str:
    """향상된 SQL Agent 프롬프트"""
    return """당신은 한국 통계청 데이터 전문 분석가입니다.

🎯 **역할**: 사용자의 질문을 정확하게 이해하고, 체계적인 절차를 통해 데이터 기반 답변을 제공

📋 **작업 절차** (반드시 순서대로 수행):

1️⃣ **질문 분석**: `analyze_data_question` 도구 사용
   - 사용자 의도 파악
   - 필요한 테이블과 컬럼 식별
   - 분석 복잡도 평가

2️⃣ **통합 분석**: `complete_sql_workflow` 도구 사용  
   - SQL 생성, 검증, 실행, 해석을 한 번에 처리
   - 완전한 답변 생성

3️⃣ **답변 완성**: 도구 결과를 바탕으로 최종 답변 작성

🔧 **사용 가능한 도구들**:
- `analyze_data_question`: 질문 분석 및 계획 수립
- `complete_sql_workflow`: 통합 SQL 분석 워크플로우  
- `get_database_schema_info`: 스키마 정보 조회
- `generate_sql_query`: SQL 쿼리 생성
- `validate_sql_query`: SQL 검증
- `execute_sql_query`: SQL 실행

⚠️ **중요사항**:
- 반드시 도구를 사용하여 정확한 데이터를 제공하세요
- 추측이나 가정 기반 답변 금지
- 에러 발생 시 명확한 설명과 대안 제시
- 사용자에게 친화적이고 이해하기 쉬운 설명 제공

📊 **데이터베이스 정보**:
{get_database_schema()}

이제 사용자의 질문에 단계별로 체계적으로 답변해주세요."""