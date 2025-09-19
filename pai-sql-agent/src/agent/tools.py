"""
SQL Agent 도구들 - LangChain Tools
한국 통계청 데이터 분석을 위한 SQL 생성, 검증, 실행 도구들
설계 원칙: Service Layer를 통한 데이터 접근 (데이터 주권 준수)
"""
import logging
from typing import List, Dict, Any
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
    logger.info("=" * 80)
    logger.info("🔧 SQL_DB_QUERY 도구 호출됨")
    logger.info(f"📝 받은 SQL 쿼리:")
    logger.info(f"   {query}")
    logger.info("=" * 80)
    
    try:
        # ✅ Service Layer를 통한 접근 (데이터 주권 준수)
        from src.database.service import get_database_service
        db_service = await get_database_service()
        
        logger.info("🚀 SQL 쿼리 실행 시작...")
        result = await db_service.execute_safe_query(query)
        
        logger.info(f"📊 쿼리 실행 완료 - 결과 수: {result.total_count}")
        
        if result.is_empty():
            logger.info("⚠️ 결과 없음 - 빈 결과 반환")
            return "쿼리 실행 결과: 데이터 없음"
        
        # 결과를 테이블 형태로 포맷팅
        formatted_result = format_query_results(result.data)
        logger.info("✅ 결과 포맷팅 완료")
        logger.info(f"📤 반환할 결과:")
        logger.info(f"   {formatted_result[:200]}...")
        
        return formatted_result

    except Exception as e:
        logger.error(f"❌ SQL 실행 오류: {str(e)}")
        return f"SQL 실행 중 오류 발생: {str(e)}"


@tool
def get_database_schema() -> str:
    """데이터베이스 스키마 정보 반환"""
    logger.info("📋 데이터베이스 스키마 정보 요청됨")
    from src.agent.prompt import DATABASE_SCHEMA_INFO
    return DATABASE_SCHEMA_INFO


@tool
async def generate_sql_query(question: str) -> str:
    """자연어 질문을 SQL 쿼리로 변환하는 도구"""
    try:
        logger.info(f"🧠 SQL 생성 시작 - 질문: {question[:100]}...")
        
        # ✅ Service Layer를 통한 LLM 접근
        from src.llm.service import get_llm_service
        llm_service = await get_llm_service()
        
        # 프롬프트 구성
        from src.agent.prompt import DATABASE_SCHEMA_INFO
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content=f"""당신은 한국 통계청 데이터 분석 전문가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

사용자 질문에 대해 적절한 PostgreSQL SELECT 쿼리를 생성해주세요.
규칙:
1. SELECT 문만 사용
2. 적절한 WHERE 조건 추가  
3. ORDER BY로 정렬 (중요도순)
4. LIMIT 30으로 결과 제한
5. 컬럼명은 스키마와 정확히 일치

쿼리만 반환하고 다른 설명은 포함하지 마세요."""),
            HumanMessage(content=question)
        ]
        
        # ✅ 수정: 기존 generate 메서드 사용
        response = await llm_service.generate(messages)
        
        # SQL 부분만 추출
        sql_query = extract_sql_from_response(response.content)
        
        logger.info(f"✅ SQL 생성 완료: {sql_query[:100]}...")
        return sql_query
        
    except Exception as e:
        logger.error(f"❌ SQL 생성 오류: {str(e)}")
        return f"SELECT 'SQL 생성 중 오류 발생: {str(e)}' as error_message;"


@tool
def validate_sql_query(query: str) -> str:
    """SQL 쿼리의 안전성을 검증하는 도구"""
    try:
        validator = SQLValidator()
        is_valid, error_msg = validator.validate(query)
        
        if is_valid:
            return f"✅ SQL 검증 성공: {query}"
        else:
            return f"❌ SQL 검증 실패: {error_msg}"
            
    except Exception as e:
        return f"❌ 검증 오류: {str(e)}"


def format_query_results(results: List[Dict[str, Any]]) -> str:
    """쿼리 결과를 테이블 형태로 포맷팅"""
    if not results:
        return "결과 없음"
    
    # 컬럼명 추출
    columns = list(results[0].keys())
    
    # 헤더 생성
    header = " | ".join(columns)
    separator = "-" * len(header)
    
    # 데이터 행 생성
    rows = []
    for row in results[:10]:  # 최대 10개 행만 표시
        row_data = []
        for col in columns:
            value = row.get(col, "")
            # None 값 처리
            if value is None:
                value = "NULL"
            # 숫자 데이터 포맷팅
            elif isinstance(value, (int, float)) and value > 999:
                value = f"{value:,}"
            # 긴 문자열 자르기
            else:
                str_value = str(value)
                if len(str_value) > 20:
                    str_value = str_value[:17] + "..."
                value = str_value
            row_data.append(value)
        rows.append(" | ".join(row_data))
    
    # 결과 조합
    result_table = [header, separator] + rows
    
    # 결과 개수 정보 추가
    if len(results) > 10:
        result_table.append(f"... (총 {len(results)}개 행 중 10개만 표시)")
    
    return "\n".join(result_table)


def extract_sql_from_response(response: str) -> str:
    """LLM 응답에서 SQL 쿼리 부분만 추출"""
    # ```sql과 ``` 사이의 내용 추출
    if "```sql" in response:
        start = response.find("```sql") + 6
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    
    # SQL 키워드로 시작하는 부분 찾기
    lines = response.split('\n')
    sql_lines = []
    in_sql = False
    
    for line in lines:
        line = line.strip()
        if line.upper().startswith('SELECT'):
            in_sql = True
        
        if in_sql:
            sql_lines.append(line)
            if line.endswith(';'):
                break
    
    if sql_lines:
        return '\n'.join(sql_lines)
    
    return response.strip()


# ===== 간소화된 유틸리티 클래스들 =====

class SQLValidator:
    """SQL 검증기 - 간소화된 버전"""
    
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
    ]
    
    def validate(self, query: str) -> tuple[bool, str]:
        """SQL 검증"""
        if not query or not query.strip():
            return False, "빈 쿼리입니다"
        
        query_upper = query.upper().strip()
        
        # SELECT로 시작하는지 확인
        if not query_upper.startswith('SELECT'):
            return False, "SELECT 문만 허용됩니다"
        
        # 위험한 키워드 확인
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"금지된 SQL 키워드: {keyword}"
        
        # 기본적인 문법 검사
        if query.count('(') != query.count(')'):
            return False, "괄호가 일치하지 않습니다"
        
        return True, ""


class SQLExecutor:
    """SQL 실행기 - 간소화된 버전"""
    
    def __init__(self, validator: SQLValidator, database_manager):
        self.validator = validator
        self.database_manager = database_manager
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """SQL 쿼리 실행"""
        try:
            # 검증
            is_valid, error_msg = self.validator.validate(query)
            if not is_valid:
                return {
                    "success": False,
                    "result": f"쿼리 검증 실패: {error_msg}",
                    "error": error_msg
                }
            
            # Service Layer를 통한 실행
            from src.database.service import get_database_service
            db_service = await get_database_service()
            
            result = await db_service.execute_safe_query(query)
            
            return {
                "success": True,
                "result": format_query_results(result.data),
                "row_count": result.total_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "result": f"실행 오류: {str(e)}",
                "error": str(e)
            }


class SQLGenerator:
    """SQL 생성기 - 간소화된 버전"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def generate(self, question: str) -> str:
        """SQL 쿼리 생성"""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from src.agent.prompt import DATABASE_SCHEMA_INFO
            
            messages = [
                SystemMessage(content=f"""한국 통계청 데이터베이스의 SQL 전문가입니다.

데이터베이스 스키마:
{DATABASE_SCHEMA_INFO}

사용자 질문에 대해 적절한 PostgreSQL SELECT 쿼리를 생성해주세요.
쿼리만 반환하고 다른 설명은 포함하지 마세요."""),
                HumanMessage(content=question)
            ]
            
            response = await self.llm.ainvoke(messages)
            return extract_sql_from_response(response.content)
            
        except Exception as e:
            logger.error(f"SQL 생성 오류: {e}")
            return f"SELECT 'SQL 생성 실패: {str(e)}' as error;"


# ===== 사용 가능한 도구 목록 =====

AVAILABLE_TOOLS = [
    sql_db_query,           # SQL 실행
    get_database_schema,    # 스키마 정보
    generate_sql_query,     # SQL 생성
    validate_sql_query,     # SQL 검증
]


# ===== 도구 설정 정보 =====

TOOL_DESCRIPTIONS = {
    "sql_db_query": "한국 통계청 데이터에서 SQL 쿼리를 안전하게 실행",
    "get_database_schema": "사용 가능한 데이터베이스 테이블과 컬럼 정보 조회",
    "generate_sql_query": "자연어 질문을 SQL 쿼리로 변환",
    "validate_sql_query": "SQL 쿼리의 안전성과 유효성 검증"
}


def get_tool_by_name(tool_name: str):
    """도구 이름으로 도구 인스턴스 반환"""
    tool_map = {tool.name: tool for tool in AVAILABLE_TOOLS}
    return tool_map.get(tool_name)