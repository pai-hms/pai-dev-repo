"""
SQL Agent 도구 모음
LLM이 사용할 SQL 쿼리 실행용 데이터베이스 도구들
"""
from typing import Optional, Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, BaseToolkit
from langchain_core.runnables import RunnableConfig

from .external_database.database import CustomSQLDatabase


class SQLExecutionToolKit(BaseToolkit):
    """SQL 쿼리를 실행하는 ToolKit"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def get_tools(self) -> list[BaseTool]:
        """SQL 실행 도구 목록 반환"""
        return [QueryExecutionTool(model_config=self.model_config)]


class QueryExecutionToolInputArgs(BaseModel):
    """SQL 쿼리 실행 도구의 입력 인자"""
    query: str = Field(..., description="A detailed and correct SQL query.")


class QueryExecutionTool(BaseTool):
    """
    SQL 쿼리 실행 도구
    LLM이 생성한 SQL 쿼리를 실제 데이터베이스에 실행하고 결과를 반환
    """

    name: str = "sql_db_query"
    description: str = """
    Execute a SQL query against the database and get back the result.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    args_schema: Type[BaseModel] = QueryExecutionToolInputArgs

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: RunnableConfig = None,
    ) -> str:
        """SQL 쿼리 실행 및 결과 반환"""
        try:
            # 설정에서 데이터베이스 URL 가져오기
            db_url = config["configurable"]["sql_agent"]["db_url"]
            
            # CustomSQLDatabase를 사용해 쿼리 실행
            db = CustomSQLDatabase.from_uri(db_url)
            result = db.run_with_headers(query)
            
            return result
            
        except Exception as e:
            # 오류 발생 시 "Error:" 접두사를 붙여서 반환 (재시도 로직이 감지함)
            return f"Error: {str(e)}"
