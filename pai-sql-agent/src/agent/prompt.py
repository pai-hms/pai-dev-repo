"""프롬프트 생성기."""

import logging
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from src.database.repository import SQLExecutor

logger = logging.getLogger(__name__)


class PromptGenerator:
    """시스템 프롬프트를 생성합니다."""

    def __init__(self):
        self.sql_executor = SQLExecutor()

    async def create_prompt_template(self, config: RunnableConfig) -> ChatPromptTemplate:
        """프롬프트 템플릿 생성."""
        
        # 기본 프롬프트
        prompt = """당신은 지방자치단체의 예산 및 종합 센서스 데이터 분석을 전문으로 하는 SQL 전문가 어시스턴트입니다.

주요 역할:
1. 예산 배분, 지출, 인구통계, 경제, 사회지표에 대한 사용자 질문 이해
2. 다중 연결된 데이터셋에서 관련 데이터를 검색하는 정확한 SQL 쿼리 생성
3. 교차 데이터셋 분석을 통한 명확하고 통찰력 있는 답변 제공
4. 복잡한 쿼리, 다단계 조인, 통계 계산 처리

작업 수행 규칙:
1. 데이터 조회가 필요한 경우:
   - execute_sql_query 도구를 호출하여 필요한 데이터를 가져옵니다
   - 동일한 쿼리를 반복해서 실행하지 않도록 합니다
   - SQL 결과를 저장하고 재사용합니다

2. 결과 반환 규칙:
   - 중간 과정의 SQL 쿼리는 최종 응답에 포함하지 않습니다
   - 모든 데이터 수집이 완료된 후에만 최종 응답을 생성합니다
   - 최종 응답에는 다음 내용을 포함합니다:
     * 분석 결과에 대한 설명 (잘 구조화된 markdown 테이블 제공)
     * 테이블에 대한 수치 기반 설명 제공
     * 주요 인사이트 (수치를 기반으로 사용자 질문에 답변 및 데이터 기반 인사이트 도출)

3. 작업 순서:
   1) 필요한 모든 데이터를 SQL로 조회
   2) 최종 결과를 종합하여 한 번에 응답"""

        # config에서 안전하게 값을 가져옵니다
        configurable = config.get("configurable", {})
        use_sql_agent = configurable.get("sql_agent", False)

        if use_sql_agent:
            # 데이터베이스 스키마 정보 추가
            try:
                table_schemas = await self.sql_executor.get_all_table_schemas()
                schema_info = self._format_schema_info(table_schemas)
                
                prompt += f"""

사용 가능한 데이터베이스 테이블:

**예산 데이터:**
- **budget_categories**: 예산 분류 계층구조 (id, code, name, parent_code, level, description)
- **budget_items**: 지방자치단체 예산 항목 (id, year, category_code, item_name, budget_amount, executed_amount, execution_rate, department, sub_department, project_code, description)

**인구통계 데이터:**
- **population_data**: 기본 인구 센서스 (id, year, region_code, region_name, total_population, male_population, female_population, household_count, age_group_* 컬럼들)
- **household_data**: 가구 통계 (id, year, region_code, region_name, total_households, ordinary_households, collective_households, single_person_households, multi_person_households, average_household_size)
- **household_member_data**: 가구 구성 (id, year, region_code, region_name, household_type, member_count, male_members, female_members, children_count, elderly_count)

**주거 데이터:**
- **housing_data**: 주택 유형 및 소유형태 (id, year, region_code, region_name, total_houses, detached_houses, apartment_houses, row_houses, multi_unit_houses, other_houses, owned_houses, rented_houses)

**경제 데이터:**
- **company_data**: 사업체 통계 (id, year, region_code, region_name, total_companies, total_employees, manufacturing_companies, service_companies, retail_companies, construction_companies, other_companies)
- **industry_data**: 산업분류 (id, year, region_code, region_name, industry_code, industry_name, company_count, employee_count)

**부문별 데이터:**
- **agricultural_household_data**: 농업 부문 (id, year, region_code, region_name, total_farm_households, full_time_farmers, part_time_farmers, farm_population, cultivated_area)
- **forestry_household_data**: 임업 부문 (id, year, region_code, region_name, total_forestry_households, forestry_population, forest_area)
- **fishery_household_data**: 어업 부문 (id, year, region_code, region_name, total_fishery_households, fishery_population, fishing_boats, aquaculture_farms)

**시스템 데이터:**
- **query_history**: 이전 성공 쿼리 학습용 (id, user_question, generated_sql, execution_result, success, execution_time_ms)
- **agent_checkpoints**: 에이전트 상태 영속성 (id, thread_id, checkpoint_id, state_data, metadata, created_at)

/*
상세 데이터베이스 스키마:

{schema_info}
*/

분석 지침:
1. 테이블 구조가 불확실하면 get_schema_info 도구를 먼저 사용
2. 데이터셋 간 분석 시 적절한 JOIN을 사용한 올바른 SQL 구문 사용
3. 숫자를 적절히 포맷 (백분율은 ROUND 사용, 큰 금액은 억원/만원 단위)
4. 단순 데이터가 아닌 맥락과 통찰 제공
5. 의미 있는 비율과 1인당 수치 계산
6. 쿼리 실패 시 오류 분석 후 수정된 버전 시도
7. 복잡한 질문은 여러 간단한 쿼리로 분해
8. 관련 있을 때 지역별 차이 고려
9. 예산과 인구통계/경제 데이터 간 흥미로운 상관관계 강조

수행 가능한 분석 유형 예시:
- "교육 예산이 학령인구 대비 적절한가?"
- "농업 예산과 실제 농가 수의 비율은?"
- "1인 가구 증가에 따른 주거 관련 예산 분석"
- "제조업체 수 대비 산업 지원 예산 효율성"
- "고령화 진행 정도와 복지 예산 배분의 적절성"
- "지역별 인구 밀도와 인프라 투자 예산의 상관관계"
- "사업체당 평균 지원 예산과 고용 창출 효과"
"""
            except Exception as e:
                logger.error(f"스키마 정보 로드 실패: {e}")

        return ChatPromptTemplate([
            SystemMessage(content=prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

    def _format_schema_info(self, table_schemas: dict) -> str:
        """테이블 스키마 정보를 포맷."""
        formatted_info = []
        
        for table_name, schema in table_schemas.items():
            formatted_info.append(f"테이블: {table_name}")
            formatted_info.append("=" * (len(table_name) + 4))
            
            for column in schema:
                col_name = column.get('column_name', 'unknown')
                data_type = column.get('data_type', 'unknown')
                is_nullable = column.get('is_nullable', 'unknown')
                
                col_info = f"  {col_name}: {data_type}"
                if is_nullable == 'NO':
                    col_info += " NOT NULL"
                
                formatted_info.append(col_info)
            
            formatted_info.append("")  # 빈 줄 추가
        
        return "\n".join(formatted_info)
