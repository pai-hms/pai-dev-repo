"""에이전트용 도구들."""

import asyncio
import uuid
from typing import List, Optional, Type, Literal

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.runnables import RunnableConfig

from src.tools.sql_tools import SQLQueryTool as BaseSQLQueryTool, SchemaInfoTool


class SQLQueryToolInputArgs(BaseModel):
    """SQL 쿼리 도구 입력 인자."""
    query: str = Field(..., description="실행할 SQL 쿼리에 대한 상세하고 정확한 설명")


class SQLQueryTool(BaseTool):
    """데이터베이스에 대해 SQL 쿼리를 실행하는 도구."""

    base_sql_tool: BaseSQLQueryTool = Field(exclude=True)
    schema_tool: SchemaInfoTool = Field(exclude=True)

    name: str = "execute_sql_query"
    description: str = """
    데이터베이스에 대해 SQL 쿼리를 생성하고 실행합니다.
    쿼리에 대한 상세하고 정확한 설명을 제공해야 합니다.
    
    사용 가능한 테이블:
    - budget_categories: 예산 분류 계층구조
    - budget_items: 지방자치단체 예산 항목
    - population_data: 센서스 인구 데이터
    - household_data: 가구 통계
    - housing_data: 주택 통계
    - company_data: 사업체 통계
    - industry_data: 산업분류별 통계
    - agricultural_household_data: 농업 가구 데이터
    - forestry_household_data: 임업 가구 데이터
    - fishery_household_data: 어업 가구 데이터
    - query_history: 쿼리 실행 이력
    """
    args_schema: Type[BaseModel] = SQLQueryToolInputArgs
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **data):
        super().__init__(**data)
        if 'base_sql_tool' not in data:
            self.base_sql_tool = BaseSQLQueryTool()
        if 'schema_tool' not in data:
            self.schema_tool = SchemaInfoTool()

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: RunnableConfig = None,
    ):
        return asyncio.run(self._arun(query, run_manager, config))

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: RunnableConfig = None,
    ):
        """SQL 쿼리를 실행하고 결과를 반환."""
        try:
            # 기본 SQL 도구를 사용하여 쿼리 실행
            result = await self.base_sql_tool._arun(query, run_manager)
            data_id = str(uuid.uuid4())[:8]

            # 결과를 파싱하여 구조화된 데이터 추출
            data = self._parse_sql_result(result)

            return f"data_id: {data_id}\n\n쿼리 실행 완료:\n{result}", {
                "sql_query": query,
                "data": data,
                "data_id": data_id,
            }
        except Exception as e:
            error_msg = f"SQL 쿼리 실행 중 오류 발생: {str(e)}"
            return error_msg, {
                "sql_query": query,
                "data": None,
                "error": error_msg,
            }

    def _parse_sql_result(self, result: str) -> List[dict]:
        """SQL 결과를 파싱하여 구조화된 데이터로 변환."""
        # 간단한 파싱 로직 - 실제로는 더 정교한 파싱이 필요할 수 있음
        lines = result.split('\n')
        
        # 테이블 형태의 결과를 찾기
        data = []
        header_found = False
        headers = []
        
        for line in lines:
            if '|' in line and not line.startswith('-'):
                if not header_found:
                    headers = [col.strip() for col in line.split('|')]
                    header_found = True
                else:
                    values = [val.strip() for val in line.split('|')]
                    if len(values) == len(headers):
                        row = dict(zip(headers, values))
                        data.append(row)
        
        return data


class SchemaInfoToolWrapper(BaseTool):
    """스키마 정보 조회 도구 래퍼."""

    schema_tool: SchemaInfoTool = Field(exclude=True)

    name: str = "get_schema_info"
    description: str = """
    데이터베이스 테이블의 스키마 정보를 조회합니다.
    특정 테이블의 스키마 정보나 모든 테이블의 스키마 정보를 가져올 수 있습니다.
    """
    args_schema: Type[BaseModel] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **data):
        super().__init__(**data)
        if 'schema_tool' not in data:
            self.schema_tool = SchemaInfoTool()

    def _run(
        self,
        table_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: RunnableConfig = None,
    ):
        return asyncio.run(self._arun(table_name, run_manager, config))

    async def _arun(
        self,
        table_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: RunnableConfig = None,
    ):
        """스키마 정보를 조회하고 반환."""
        return await self.schema_tool._arun(table_name, run_manager)
