"""에이전트용 SQL 실행 도구."""

import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolUse

from src.database.repository import SQLExecutor


class SQLQueryInput(BaseModel):
    """SQL 쿼리 도구 입력 스키마."""
    query: str = Field(description="실행할 SQL 쿼리")


class SQLQueryTool(BaseTool):
    """데이터 주권 원칙을 따르는 SQL 쿼리 실행 도구."""
    
    name: str = "execute_sql_query"
    description: str = """
    지방자치단체 예산 및 센서스 데이터베이스에 대해 SQL 쿼리를 실행합니다.
    
    사용 가능한 테이블:
    - budget_categories: 예산 분류 계층구조 (code, name, parent_code, level)
    - budget_items: 지방자치단체 예산 항목 (year, category_code, item_name, budget_amount, executed_amount, execution_rate, department)
    - population_data: 센서스 인구 데이터 (year, region_code, region_name, total_population, male_population, female_population, household_count, 연령대별)
    - household_data: 가구 통계 (total_households, single_person_households, average_household_size 등)
    - housing_data: 주택 통계 (total_houses, detached_houses, apartment_houses, owned_houses 등)
    - company_data: 사업체 통계 (total_companies, total_employees, manufacturing_companies 등)
    - industry_data: 산업분류별 통계 (industry_code, industry_name, company_count, employee_count)
    - agricultural_household_data: 농업 가구 데이터
    - forestry_household_data: 임업 가구 데이터
    - fishery_household_data: 어업 가구 데이터
    - query_history: 학습용 이전 쿼리 실행 이력
    
    이 도구 사용법:
    1. 분류, 부서, 금액별 예산 데이터 조회
    2. 인구통계 분석
    3. 1인당 분석을 위한 예산과 인구 데이터 조인
    4. 예산 집행률 및 트렌드 계산
    5. 교차 부문 분석 (예산-인구-경제-주거)
    6. 지역별 비교 분석
    
    항상 올바른 SQL 구문을 사용하고 데이터 타입에 주의하세요.
    """
    args_schema = SQLQueryInput
    
    def __init__(self):
        super().__init__()
        self.sql_executor = SQLExecutor()
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolUse] = None,
    ) -> str:
        """SQL 쿼리 동기 실행 (권장하지 않음)."""
        raise NotImplementedError("비동기 버전을 사용하세요")
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolUse] = None,
    ) -> str:
        """SQL 쿼리 비동기 실행."""
        start_time = time.time()
        
        try:
            # SQL 쿼리 실행
            results = await self.sql_executor.execute_sql_query(query)
            execution_time = int((time.time() - start_time) * 1000)
            
            # 에이전트용 결과 포맷
            if not results:
                return "쿼리가 성공적으로 실행되었지만 결과가 없습니다."
            
            # 에이전트 과부하 방지를 위한 결과 제한
            if len(results) > 100:
                limited_results = results[:100]
                result_text = self._format_results(limited_results)
                result_text += f"\n\n(총 {len(results)}개 결과 중 처음 100개 표시)"
            else:
                result_text = self._format_results(results)
            
            result_text += f"\n\n실행 시간: {execution_time}ms"
            return result_text
            
        except Exception as e:
            error_msg = f"SQL 실행 오류: {str(e)}"
            if run_manager:
                run_manager.on_tool_error(error_msg)
            return error_msg
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """에이전트 사용을 위한 쿼리 결과 포맷."""
        if not results:
            return "결과를 찾을 수 없습니다."
        
        # 첫 번째 결과에서 컬럼명 가져오기
        columns = list(results[0].keys())
        
        # 포맷된 테이블 생성
        formatted_lines = []
        
        # 헤더
        header = " | ".join(columns)
        formatted_lines.append(header)
        formatted_lines.append("-" * len(header))
        
        # 데이터 행
        for row in results:
            row_values = []
            for col in columns:
                value = row.get(col)
                if value is None:
                    row_values.append("NULL")
                else:
                    row_values.append(str(value))
            formatted_lines.append(" | ".join(row_values))
        
        return "\n".join(formatted_lines)


class SchemaInfoInput(BaseModel):
    """스키마 정보 도구 입력 스키마."""
    table_name: Optional[str] = Field(
        default=None, 
        description="스키마를 가져올 특정 테이블명, 또는 모든 테이블의 경우 None"
    )


class SchemaInfoTool(BaseTool):
    """데이터베이스 스키마 정보 조회 도구."""
    
    name: str = "get_schema_info"
    description: str = """
    테이블의 데이터베이스 스키마 정보를 가져옵니다.
    
    이 도구 사용법:
    1. 쿼리 작성 전 테이블 구조 이해
    2. 컬럼명, 데이터 타입, 제약조건 확인
    3. 데이터베이스의 사용 가능한 테이블 탐색
    
    특정 테이블 스키마의 경우 table_name 매개변수 제공, 모든 테이블의 경우 비워두세요.
    """
    args_schema = SchemaInfoInput
    
    def __init__(self):
        super().__init__()
        self.sql_executor = SQLExecutor()
    
    def _run(
        self,
        table_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolUse] = None,
    ) -> str:
        """Get schema info synchronously (not recommended)."""
        raise NotImplementedError("Use async version instead")
    
    async def _arun(
        self,
        table_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolUse] = None,
    ) -> str:
        """Get schema info asynchronously."""
        try:
            if table_name:
                # Get schema for specific table
                schema_info = await self.sql_executor.get_table_schema(table_name)
                return self._format_table_schema(table_name, schema_info)
            else:
                # Get schema for all tables
                all_schemas = await self.sql_executor.get_all_table_schemas()
                formatted_schemas = []
                
                for table, schema in all_schemas.items():
                    formatted_schemas.append(self._format_table_schema(table, schema))
                
                return "\n\n".join(formatted_schemas)
                
        except Exception as e:
            error_msg = f"Schema info error: {str(e)}"
            if run_manager:
                run_manager.on_tool_error(error_msg)
            return error_msg
    
    def _format_table_schema(self, table_name: str, schema_info: List[Dict[str, Any]]) -> str:
        """Format table schema information."""
        if not schema_info:
            return f"Table '{table_name}' not found or has no columns."
        
        lines = [f"Table: {table_name}"]
        lines.append("=" * (len(table_name) + 7))
        
        for column in schema_info:
            col_name = column.get('column_name', 'unknown')
            data_type = column.get('data_type', 'unknown')
            is_nullable = column.get('is_nullable', 'unknown')
            default_val = column.get('column_default')
            max_length = column.get('character_maximum_length')
            
            col_info = f"  {col_name}: {data_type}"
            
            if max_length:
                col_info += f"({max_length})"
            
            if is_nullable == 'NO':
                col_info += " NOT NULL"
            
            if default_val:
                col_info += f" DEFAULT {default_val}"
            
            lines.append(col_info)
        
        return "\n".join(lines)
