"""
SQL Agent 도구들
데이터와 로직 일체화 원칙에 따라 관련 기능을 함께 관리
"""
import re
import logging
from typing import Tuple, Optional, Dict, Any
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from src.database.repository import DatabaseService

logger = logging.getLogger(__name__)


# ===== SQL 검증기 =====

class SQLValidator:
    """SQL 검증 - 단일 책임"""
    
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE'
    ]
    
    ALLOWED_TABLES = [
        'population_stats', 'household_stats', 'house_stats', 
        'company_stats', 'farm_household_stats', 'forestry_household_stats',
        'fishery_household_stats', 'household_member_stats', 'industry_code_stats'
    ]
    
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """쿼리 검증"""
        if not query or not query.strip():
            return False, "빈 쿼리입니다"
        
        query_upper = query.upper()
        
        # 위험한 키워드 검사
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"허용되지 않은 키워드: {keyword}"
        
        # SELECT 문 확인
        if not query_upper.strip().startswith('SELECT'):
            return False, "SELECT 문만 허용됩니다"
        
        # 다중 쿼리 방지
        semicolon_count = query.count(';')
        if semicolon_count > 1:
            return False, "다중 쿼리는 허용되지 않습니다"
        elif semicolon_count == 1 and not query.strip().endswith(';'):
            return False, "다중 쿼리는 허용되지 않습니다"
        
        # 테이블 검증
        return self._validate_tables(query_upper)
    
    def _validate_tables(self, query_upper: str) -> Tuple[bool, Optional[str]]:
        """테이블 이름 검증"""
        table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query_upper)
        
        for table in tables:
            if table.lower() not in self.ALLOWED_TABLES:
                return False, f"허용되지 않은 테이블: {table}"
        
        return True, None


# ===== SQL 실행기 =====

class SQLExecutor:
    """SQL 실행 - 단일 책임"""
    
    def __init__(self, validator: SQLValidator, db_manager):
        self.validator = validator
        self.db_manager = db_manager
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """SQL 실행"""
        try:
            # 검증
            is_valid, error_msg = self.validator.validate(query)
            if not is_valid:
                return {
                    "success": False,
                    "result": f"쿼리 검증 실패: {error_msg}",
                    "error": error_msg
                }
            
            # 실행
            async with self.db_manager.get_async_session() as session:
                db_service = DatabaseService(session)
                results = await db_service.execute_raw_query(query)
            
            # 포맷팅
            formatted_result = self._format_results(results)
            
            return {
                "success": True,
                "result": formatted_result,
                "row_count": len(results) if results else 0
            }
            
        except Exception as e:
            logger.error(f"SQL 실행 오류: {e}")
            return {
                "success": False,
                "result": f"SQL 실행 중 오류: {str(e)}",
                "error": str(e)
            }
    
    def _format_results(self, results: list) -> str:
        """결과 포맷팅"""
        if not results:
            return "쿼리 결과가 없습니다."
        
        # 결과가 리스트가 아닐 경우 처리
        if not isinstance(results, list):
            return f"결과: {results}"
        
        try:
            headers = list(results[0].keys())
            table_lines = []
            
            # 헤더
            header_line = " | ".join(str(h) for h in headers)
            table_lines.append(header_line)
            table_lines.append("-" * len(header_line))
            
            # 데이터 (최대 50개)
            max_rows = min(50, len(results))
            for i in range(max_rows):
                row = results[i]
                row_line = " | ".join(str(row.get(h, "")) for h in headers)
                table_lines.append(row_line)
            
            if len(results) > max_rows:
                table_lines.append(f"... ({len(results) - max_rows}개 행 더 있음)")
            
            return f"쿼리 실행 완료 ({len(results)}개 행):\n\n" + "\n".join(table_lines)
        except Exception as e:
            return f"결과 포맷팅 오류: {str(e)}, 원본 결과: {results}"


# ===== SQL 생성기 =====

class SQLGenerator:
    """SQL 생성 - 단일 책임"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def generate(self, question: str, schema_info: str = "") -> str:
        """SQL 생성 - 개선된 프롬프트"""
        try:
            # 질문에서 지역 정보 추출
            region_info = self._extract_region_info(question)
            
            prompt_template = """
당신은 한국 통계 데이터 전문 SQL 개발자입니다.
다음 질문에 대해 정확하고 효율적인 PostgreSQL 쿼리를 생성하세요.

질문: {question}

## 데이터베이스 스키마
{schema_info}

## 지역 정보 분석
{region_info}

## 중요한 쿼리 작성 규칙
1. **행정구역 검색**: 반드시 adm_cd(행정구역코드) 사용
   - 포항시 남구 → adm_cd = '47111'
   - 포항시 북구 → adm_cd = '47113'
   - 서울특별시 → adm_cd = '11'

2. **비교 쿼리**: 여러 지역 비교시 IN 절 사용
   - WHERE adm_cd IN ('47111', '47113')

3. **연도 조건**: 최신 데이터 우선 (2023년)
   - WHERE year = 2023

4. **결과 정렬**: 의미있는 순서로 정렬
   - ORDER BY company_cnt DESC (사업체 수 내림차순)

## 출력 형식
```sql
[PostgreSQL 쿼리만 작성]
```

SQL 쿼리:
"""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm
            
            result = await chain.ainvoke({
                "question": question,
                "schema_info": schema_info or self._get_default_schema(),
                "region_info": region_info
            })
            
            return self._extract_sql(result.content)
            
        except Exception as e:
            logger.error(f"SQL 생성 오류: {e}")
            return f"-- 오류: SQL 생성 실패 - {str(e)}"
    
    def _extract_sql(self, llm_response: str) -> str:
        """LLM 응답에서 SQL 추출"""
        lines = llm_response.split('\n')
        sql_lines = []
        in_sql_block = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('```sql'):
                in_sql_block = True
                continue
            elif line.startswith('```') and in_sql_block:
                break
            elif in_sql_block and line:
                sql_lines.append(line)
        
        # 대체 추출
        if not sql_lines:
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SELECT'):
                    sql_lines.append(line)
                    break
        
        return '\n'.join(sql_lines) if sql_lines else "SELECT 1; -- 생성 실패"
    
    def _extract_region_info(self, question: str) -> str:
        """질문에서 지역 정보 추출 및 분석"""
        question_lower = question.lower()
        regions = []
        
        # 포항시 관련
        if "포항" in question:
            if "남구" in question:
                regions.append("포항시 남구 (adm_cd: '47111')")
            if "북구" in question:
                regions.append("포항시 북구 (adm_cd: '47113')")
            if "남구" not in question and "북구" not in question:
                regions.append("포항시 전체 (남구: '47111', 북구: '47113')")
        
        # 서울 관련
        if "서울" in question:
            regions.append("서울특별시 (adm_cd: '11')")
        
        # 비교 키워드 확인
        comparison_keywords = ["비교", "vs", "대비", "차이"]
        is_comparison = any(keyword in question for keyword in comparison_keywords)
        
        if regions:
            result = f"감지된 지역: {', '.join(regions)}"
            if is_comparison and len(regions) >= 2:
                result += "\n비교 분석 필요: 여러 지역 데이터를 함께 조회"
            return result
        else:
            return "특정 지역이 명시되지 않음 - 전국 또는 상위 지역 데이터 조회"
    
    def _get_default_schema(self) -> str:
        """기본 스키마 정보"""
        return """
주요 테이블:
- population_stats: 인구 통계 (year, adm_cd, adm_nm, tot_ppltn, avg_age)
  * 인구 관련 질문시 사용: 총인구(tot_ppltn), 평균연령(avg_age)
- company_stats: 사업체 통계 (year, adm_cd, adm_nm, company_cnt, employee_cnt)  
  * 사업체/기업 관련 질문시 사용: 사업체수(company_cnt), 종사자수(employee_cnt)

행정구역코드 매핑:
- 경상북도: '47' (시도), 경주시: '47130', 안동시: '47170', 김천시: '47150'
- 포항시 남구: '47111', 포항시 북구: '47113'  
- 서울특별시: '11'

중요한 쿼리 규칙:
- 인구 질문 → population_stats 테이블 사용
- 사업체 질문 → company_stats 테이블 사용
- 경상북도 시군구: WHERE adm_cd LIKE '47%' AND LENGTH(adm_cd) = 5
"""


# ===== LangChain Tool 래퍼 =====

@tool
async def execute_sql_query(query: str) -> str:
    """SQL 쿼리 실행 도구"""
    from .container import get_service
    
    executor = await get_service("sql_executor")
    result = await executor.execute(query)
    
    if result["success"]:
        return result["result"]
    else:
        return f"오류: {result['result']}"


# 사용 가능한 도구 목록
AVAILABLE_TOOLS = [execute_sql_query]