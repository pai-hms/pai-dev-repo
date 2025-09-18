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

**8. household_member_stats (가구원 현황 통계)**
   기본 정보: year, adm_cd, adm_nm, data_type, gender, age_from, age_to
   가구원: population(가구원수)

**주요 테이블별 용도:**
- **인구 조회**: population_stats (가장 포괄적인 데이터)
- **사업체 조회**: company_stats 또는 population_stats (둘 다 사용 가능)
- **가구원수 조회**: household_stats (avg_household_size 컬럼)

**행정구역코드:**
- 서울: '11' / 경기: '41' / 부산: '47' 
- 부산 해운대구: '47111' / 부산 수영구: '47113'

**컬럼 주의사항:**
population_stats: corp_cnt (사업체수)
company_stats: company_cnt (사업체수)  
household_stats: avg_household_size (평균가구원수)

최신 데이터는 2023년 기준!
"""

# ========================================
# 행정구역 코드 매핑 정보
# ========================================

REGION_CODE_MAPPING = """
### 행정구역 코드 체계
- **전국**: null 또는 공백
- **시도(2자리)**: 서울(11), 부산(26), 대구(27), 인천(28), 광주(29), 대전(30), 울산(31), 세종(36), 경기(41), 강원(42), 충북(43), 충남(44), 전북(45), 전남(46), 경북(47), 경남(48), 제주(50)
- **시군구(5자리)**: 시도코드 + 시군구코드 (예: 서울 종로구 11110)
- **읍면동(8자리)**: 시군구코드 + 읍면동코드 (예: 서울 종로구 청운효자동 11110101)

### 주요 지역 코드:
- 서울특별시: '11'
- 경기도: '41' 
- 부산광역시: '47'
- 부산 해운대구: '47111'
- 부산 수영구: '47113'
- 서울 강남구: '11680'
- 서울 종로구: '11110'
"""

# ========================================
# SGIS API 통계 정보 (info_api 규칙 기반)
# ========================================

SGIS_API_INFO = """
### SGIS API 주요 통계 조회 가능 항목

**총조사 주요지표 조회 API**
- 총인구(tot_ppltn), 평균나이(avg_age), 인구밀도(ppltn_dnsty)
- 노령화지수(aged_child_idx), 노년부양비(oldage_suprt_per), 유년부양비(juv_suprt_per)
- 총가구(tot_family), 평균가구원수(avg_fmember_cnt), 총주택(tot_house)
- 농가/임가/어가 관련: nongga_cnt, imga_cnt, naesuoga_cnt, haesuoga_cnt
- 사업체: employee_cnt(종업원수), corp_cnt(사업체수)

**인구통계 API (searchpopulation)**
- 행정구역별 인구수(population) 조회

**가구통계 API (household)**
- 가구수(household_cnt), 총 가구원수(family_member_cnt), 평균가구원수(avg_family_member_cnt)

**주택통계 API (house)**
- 주택수(house_cnt) 조회

**사업체통계 API (company)**
- 사업체수(corp_cnt), 종사자수(tot_worker) 조회

**농가/임가/어가통계 API**
- 농가수(farm_cnt), 임가수(forestry_cnt), 어가수(fishery_cnt)
- 각각의 인구수 및 평균인구수 제공

**가구원통계 API (householdmember)**
- 농가/임가/어가별 가구원 통계
- 성별, 연령대별 세분화 가능

**연도별 데이터 범위:**
- 인구/주택: 2015년~2023년
- 사업체: 2000년~2023년
- 농림어업: 2000년, 2005년, 2010년, 2015년, 2020년
"""

# ========================================
# SQL 생성 프롬프트 템플릿
# ========================================

SQL_GENERATION_PROMPT = """
당신은 한국의 통계청 데이터를 분석하는 PostgreSQL 전문가입니다.

질문: {question}

## 사용 가능한 데이터베이스 스키마 (실제 DB 기반)
{schema_info}

## 지역 코드 정보
{region_info}

## **중요 컬럼 매핑** - 반드시 정확히 사용할 것!

### 사업체수 조회시 주의사항:
1. **company_stats**: company_cnt (사업체수) 
2. **population_stats**: corp_cnt (사업체수) 
3. **household_stats**: avg_household_size (평균가구원수) 

### 예시 쿼리 패턴:
- 사업체수 조회시 company_stats 테이블의 **company_cnt** 컬럼 사용
- 부산 해운대구: adm_cd = '47111', 수영구: adm_cd = '47113'  
- 2023년 최신 데이터: WHERE year = 2023
- 다중지역: WHERE adm_cd IN ('47111', '47113')
- 순위 정렬: ORDER BY 컬럼명 DESC

### SQL 작성 예시:
```sql
-- 부산 구별 사업체수 조회
SELECT adm_nm, company_cnt 
FROM company_stats 
WHERE adm_cd IN ('47111', '47113') AND year = 2023
ORDER BY company_cnt DESC;

-- 서울시 총 인구수 조회
SELECT adm_nm, tot_ppltn
FROM population_stats 
WHERE adm_cd = '11' AND year = 2023;

-- 전국 평균가구원수 상위 지역 조회
SELECT adm_nm, avg_household_size
FROM household_stats 
WHERE year = 2023 AND avg_household_size IS NOT NULL
ORDER BY avg_household_size DESC
LIMIT 10;
```

## 최종 답변
```sql
[사용자 질문에 맞는 PostgreSQL 쿼리 작성]
```

SQL:
"""

# ========================================
# ReAct Agent 프롬프트
# ========================================

REACT_AGENT_INITIAL_PROMPT = """
당신은 한국 통계청 데이터를 분석하는 전문 SQL 에이전트입니다.

=== 사용자 질문 ===
{question}

=== 데이터베이스 스키마 ===
{schema_info}

=== 지시사항 ===
사용자의 질문을 분석한 후 적절한 SQL 쿼리를 생성하여 execute_sql_query 도구를 사용해 실행하세요.

주의사항:
1. 지역 코드를 정확히 매핑하여 사용 (예: 서울 '11', 부산 '47')
2. 최신 연도 데이터를 우선 사용 (2023년)
3. SELECT 문만 사용하세요
4. 결과는 적절히 제한하여 반환 (LIMIT 10 등)

반드시 execute_sql_query 도구를 사용해 쿼리를 실행하세요.
"""

REACT_AGENT_RESPONSE_PROMPT = """
사용자 질문: {question}
SQL 실행 결과: {sql_result}

위 SQL 실행 결과를 바탕으로 사용자의 질문에 대한 명확하고 도움이 되는 답변을 작성해주세요.

포함사항:
1. 질문에 대한 직접적인 답변 제공
2. 중요한 수치나 통계 정보 강조
3. 필요시 추가적인 인사이트나 해석 제공
4. 데이터 출처 및 기준 연도 명시

최종 답변:
"""

# ========================================
# 통합 Agent 프롬프트
# ========================================

REQUEST_CLASSIFICATION_PROMPT = """
다음은 사용자 입력을 분류하는 프롬프트입니다.

사용자 입력: {user_input}

다음 중 하나로 분류하세요:
1. "sql_query": 인구, 가구, 사업체 등의 통계 데이터 조회 질문 (인구, 사업체, 가구 등)
2. "general": 일반적인 대화, 인사, 도움말 등의 질문
3. "greeting": 인사말
4. "help": 도움말 요청

응답 형식:
request_type: [분류결과]
confidence: [0.0-1.0 신뢰도]
reason: [분류 이유]
"""

GENERAL_CONVERSATION_PROMPT = """
당신은 한국 통계청 데이터를 분석하는 전문 AI 어시스턴트입니다.

사용자: {user_input}

다음 원칙을 지켜주세요:
1. 친근하고 도움이 되도록 응답
2. 통계 데이터에 대한 질문이면 구체적인 예시 제공
3. 간결하고 명확한 답변

답변:
"""

RESPONSE_SYNTHESIS_PROMPT = """
사용자의 질문에 대한 SQL 실행 결과를 자연스럽게 설명해주세요.

사용자 질문: {user_input}
SQL 실행 결과: {sql_result}

다음 원칙을 지켜주세요:
1. 결과를 이해하기 쉽게 설명하기
2. 사용자의 의도에 맞는 답변 제공
3. 중요한 수치 정보나 트렌드 강조
4. 필요시 추가적인 인사이트나 해석 제공

최종 답변:
"""

# ========================================
# 미리 정의된 응답 템플릿
# ========================================

GREETING_RESPONSE = """
안녕하세요! 한국 통계청 데이터를 분석하는 전문 AI 어시스턴트입니다. 인구, 가구, 사업체 등의 통계 정보를 궁금한 점을 물어보세요.
"""

HELP_RESPONSE = """
**제가 도움드릴 수 있는 질문들:**

**인구 통계:**
- 2023년 서울시의 인구는?
- 경기도에서 인구가 가장 많은 시군구는?

**사업체 통계:**
- 부산시 구별 사업체수는 얼마나 될까
- 2023년 전국에서 사업체가 가장 많은 지역은?

**가구/주택 통계:**
- 경기도의 평균 가구원수는 얼마인가요?
- 서울시의 1인 가구 비율은 어떻게 될까

무엇을 도와드릴까요?
"""

# ========================================
# 쿼리 생성 서비스용 프롬프트
# ========================================

QUERY_GENERATION_SERVICE_PROMPT = """
다음 텍스트와 관련된 일반적인 질문 쿼리를 5개 생성해주세요.
각 쿼리는 한국의 통계청 일반인이 물어볼 만한 자연스러운 질문이어야 합니다.

텍스트:
{text}

다음 형식의 JSON으로 반환하세요:
{{
    "queries": [
        {{"query": "질문 1", "reason": "생성 이유"}},
        {{"query": "질문 2", "reason": "생성 이유"}},
        {{"query": "질문 3", "reason": "생성 이유"}},
        {{"query": "질문 4", "reason": "생성 이유"}},
        {{"query": "질문 5", "reason": "생성 이유"}}
    ]
}}
"""

# ========================================
# 오류 처리 메시지 템플릿
# ========================================

ERROR_HANDLING_PROMPTS = {
    "sql_syntax_error": "SQL 문법 오류가 발생했습니다. 쿼리를 다시 확인해 주세요.",
    "table_not_found": "테이블을 찾을 수 없습니다. 스키마 정보를 확인해주세요.",
    "column_not_found": "컬럼을 찾을 수 없습니다. 컬럼명을 확인해주세요.",
    "no_data": "조회된 데이터가 없습니다. 다른 조건으로 검색해보세요.",
    "connection_error": "데이터베이스 연결 오류가 발생했습니다.",
}

# ========================================
# 프롬프트 유틸리티 함수들
# ========================================

def get_sql_generation_prompt(question: str, region_info: str = "", schema_info: str = None) -> str:
    """SQL 생성용 프롬프트 반환"""
    return SQL_GENERATION_PROMPT.format(
        question=question,
        region_info=region_info or "지역 정보가 명시되지 않음 - 전국 또는 특정 지역 코드를 사용해 검색",
        schema_info=schema_info or DATABASE_SCHEMA_INFO
    )

def get_react_agent_initial_prompt(question: str, schema_info: str = None) -> str:
    """ReAct Agent 초기 프롬프트 반환"""
    return REACT_AGENT_INITIAL_PROMPT.format(
        question=question,
        schema_info=schema_info or DATABASE_SCHEMA_INFO
    )

def get_react_agent_response_prompt(question: str, sql_result: str) -> str:
    """ReAct Agent 응답 생성 프롬프트 반환"""
    return REACT_AGENT_RESPONSE_PROMPT.format(
        question=question,
        sql_result=sql_result
    )

def get_request_classification_prompt(user_input: str) -> str:
    """요청 분류 프롬프트 반환"""
    return REQUEST_CLASSIFICATION_PROMPT.format(user_input=user_input)

def get_general_conversation_prompt(user_input: str) -> str:
    """일반 대화 프롬프트 반환"""
    return GENERAL_CONVERSATION_PROMPT.format(user_input=user_input)

def get_response_synthesis_prompt(user_input: str, sql_result: str) -> str:
    """응답 합성용 프롬프트 반환"""
    return RESPONSE_SYNTHESIS_PROMPT.format(
        user_input=user_input,
        sql_result=sql_result
    )

def get_query_generation_service_prompt(text: str) -> str:
    """쿼리 생성 서비스용 프롬프트 반환"""
    return QUERY_GENERATION_SERVICE_PROMPT.format(text=text)

def get_database_schema() -> str:
    """데이터베이스 스키마 정보 반환"""
    return DATABASE_SCHEMA_INFO

def get_region_code_mapping() -> str:
    """행정구역 코드 매핑 정보 반환"""
    return REGION_CODE_MAPPING

def get_sgis_api_info() -> str:
    """SGIS API 정보 반환"""
    return SGIS_API_INFO

def get_error_message(error_type: str) -> str:
    """오류 타입별 메시지 반환"""
    return ERROR_HANDLING_PROMPTS.get(error_type, "알 수 없는 오류가 발생했습니다.")

# ========================================
# 시스템 프롬프트 통합 관리 함수
# ========================================

def get_system_prompt(prompt_type: str = "default", **kwargs) -> str:
    """
    시스템 프롬프트 통합 반환
    
    Args:
        prompt_type: 프롬프트 타입 ('sql_generation', 'react_initial', 'classification' 등)
        **kwargs: 프롬프트 템플릿에 필요한 변수들
    
    Returns:
        str: 완성된 시스템 프롬프트
    """
    prompt_map = {
        "sql_generation": get_sql_generation_prompt,
        "react_initial": get_react_agent_initial_prompt,
        "react_response": get_react_agent_response_prompt,
        "classification": get_request_classification_prompt,
        "general": get_general_conversation_prompt,
        "synthesis": get_response_synthesis_prompt,
        "query_service": get_query_generation_service_prompt,
    }
    
    if prompt_type in prompt_map:
        return prompt_map[prompt_type](**kwargs)
    else:
        return DATABASE_SCHEMA_INFO  # 기본값