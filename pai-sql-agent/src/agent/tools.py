"""
SQL Agent 도구들 - 간소화된 버전
"""
import logging
from typing import List
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def sql_db_query(query: str) -> str:
    """
    SQL 쿼리를 실행하고 결과를 반환하는 도구
    
    Args:
        query: 실행할 SQL 쿼리
    
    Returns:
        쿼리 실행 결과
    """
    try:
        from .container import get_container
        
        container = await get_container()
        db_manager = await container.database_manager()
        
        # SQL 실행
        async with db_manager.get_async_session() as session:
            from src.database.repository import DatabaseService
            db_service = DatabaseService(session)
            results = await db_service.execute_raw_query(query)
            
            if not results:
                return "쿼리 실행 결과: 데이터 없음"
            
            # 결과 포맷팅
            if isinstance(results, list) and results:
                columns = list(results[0].keys())
                header = " | ".join(columns)
                
                rows = []
                for row in results[:10]:  # 최대 10개 행
                    row_data = []
                    for col in columns:
                        value = row.get(col, '')
                        if value is None:
                            value = 'NULL'
                        elif isinstance(value, (int, float)):
                            value = f"{value:,}"
                        else:
                            value = str(value)[:50]
                        row_data.append(value)
                    rows.append(" | ".join(row_data))
                
                result = f"{header}\n" + "\n".join(rows)
                if len(results) > 10:
                    result += f"\n... (총 {len(results)}개 중 10개만 표시)"
                
                return result
            else:
                return str(results)
                
    except Exception as e:
        logger.error(f"SQL 쿼리 실행 오류: {e}")
        return f"Error: {str(e)}"


@tool
def get_database_schema() -> str:
    """데이터베이스 스키마 정보 반환"""
    from src.agent.prompt import DATABASE_SCHEMA_INFO
    return DATABASE_SCHEMA_INFO


# 사용 가능한 도구 목록
AVAILABLE_TOOLS = [sql_db_query, get_database_schema]


# 기존 클래스들도 간소화
class SQLValidator:
    """SQL 검증기"""
    
    def validate(self, sql: str) -> tuple[bool, str]:
        """SQL 검증"""
        if not sql.strip():
            return False, "SQL이 비어있습니다"
        
        # 기본적인 DML 체크
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER']
        sql_upper = sql.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"위험한 SQL 키워드가 포함되어 있습니다: {keyword}"
        
        return True, ""


class SQLExecutor:
    """SQL 실행기"""
    
    def __init__(self, validator: SQLValidator, database_manager):
        self.validator = validator
        self.database_manager = database_manager


class SQLGenerator:
    """SQL 생성기"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def generate(self, question: str) -> str:
        """SQL 쿼리 생성"""
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.agent.prompt import DATABASE_SCHEMA_INFO
        
        messages = [
            SystemMessage(content=f"""한국 통계청 데이터베이스의 SQL 전문가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

사용자 질문에 대해 적절한 PostgreSQL 쿼리를 생성해주세요.
쿼리만 반환하고 다른 설명은 포함하지 마세요."""),
            HumanMessage(content=question)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content