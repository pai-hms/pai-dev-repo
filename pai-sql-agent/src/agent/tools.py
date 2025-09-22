"""
SQL Agent 도구들 - LangChain Tools
한국 통계청 데이터 분석을 위한 SQL 생성, 검증, 실행 도구들
"""
import logging
from typing import List, Dict, Any

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.prompt import DATABASE_SCHEMA_INFO
from src.agent.utils import estimate_context_tokens, should_filter_context
from src.agent.settings import get_settings
from src.database.service import get_database_service
from src.llm.service import get_llm_service
from src.llm.settings import LLMSettings

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
    logger.info("SQL_DB_QUERY 도구 호출됨")
    logger.info(f"받은 SQL 쿼리:")
    logger.info(f"   {query}")
    logger.info("=" * 80)
    
    try:
        # Service Layer를 통한 접근
        db_service = await get_database_service()
        
        logger.info("SQL 쿼리 실행 시작...")
        result = await db_service.execute_custom_query(query)
        
        logger.info(f"쿼리 실행 완료 - 결과 수: {result.row_count}")
        
        if not result.success or not result.data:
            logger.info("결과 없음 또는 실행 실패")
            if not result.success:
                return f"쿼리 실행 실패: {result.error}"
            return "쿼리 실행 결과: 데이터 없음"
        
        # 결과를 테이블 형태로 포맷팅
        formatted_result = format_query_results(result.data)
        logger.info("결과 포맷팅 완료")
        
        # 컨텍스트 길이 체크 및 필터링
        settings = get_settings()
        # 기본 모델 사용 (LLM 설정에서 가져옴)
        llm_settings = LLMSettings()
        current_model = llm_settings.DEFAULT_MODEL_KEY
        
        if should_filter_context(formatted_result, settings.DOCUMENT_MAX_TOKENS, current_model):
            current_tokens = estimate_context_tokens(formatted_result, current_model)
            logger.warning(f"SQL 결과가 토큰 제한 초과 ({current_tokens} > {settings.DOCUMENT_MAX_TOKENS})")
            
            # 결과 행 수 제한으로 크기 줄이기
            lines = formatted_result.split('\n')
            if len(lines) > 20:  # 헤더 + 최대 15개 행만 유지
                truncated_result = '\n'.join(lines[:17]) + f'\n... (총 {result.row_count}개 행 중 15개만 표시)'
                logger.info(f"결과 크기 제한: {len(lines)} → 17 라인")
                formatted_result = truncated_result
        
        logger.info(f"반환할 결과:")
        logger.info(f"   {formatted_result[:200]}...")
        
        return formatted_result

    except Exception as e:
        logger.error(f"SQL 실행 오류: {str(e)}")
        return f"SQL 실행 중 오류 발생: {str(e)}"


@tool
def get_database_schema() -> str:
    """데이터베이스 스키마 정보 반환"""
    logger.info("데이터베이스 스키마 정보 요청됨")
    return DATABASE_SCHEMA_INFO


# generate_sql_query와 validate_sql_query 도구 제거됨
# 실제로는 sql_db_query만 주로 사용되며, SQL 생성은 Agent가 직접 처리


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


# ===== 유틸리티 클래스들 제거됨 =====
# SQLValidator, SQLExecutor, SQLGenerator는 실제로 사용되지 않음
# sql_db_query 도구에서 직접 DatabaseService를 사용하는 방식으로 단순화


# ===== 사용 가능한 도구 목록 =====

AVAILABLE_TOOLS = [
    sql_db_query,           # SQL 실행
    get_database_schema,    # 스키마 정보
]


# ===== 도구 설정 정보 (미사용으로 제거) =====
# TOOL_DESCRIPTIONS는 실제로 어디서도 참조되지 않음

