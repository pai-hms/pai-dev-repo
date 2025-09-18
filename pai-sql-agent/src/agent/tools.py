"""
SQL Agent 도구들
한국 통계청 데이터 분석을 위한 SQL 실행 및 검증 도구들을 제공

설계 원칙:
- 단일 책임 원칙: 각 클래스는 하나의 명확한 역할만 담당
- 데이터 주권: SQL 검증과 실행을 분리하여 안전성 확보
- 의존성 주입: 외부 의존성을 주입받아 테스트 용이성 향상
"""
import re
import logging
from typing import Tuple, Optional, Dict, Any, List
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from src.database.repository import DatabaseService
from .prompt import get_sql_generation_prompt, get_database_schema

logger = logging.getLogger(__name__)


# ===== SQL 검증기 =====

class SQLValidator:
    """SQL 쿼리 검증기 - 보안 및 안전성 검증"""
    
    # 위험한 SQL 키워드 (읽기 전용 보장)
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT'
    ]
    
    # 허용된 테이블 목록 (통계청 데이터만)
    ALLOWED_TABLES = [
        # 인구 관련 테이블들
        'population_stats', 'population_search_stats',
        # 가구 관련 테이블들  
        'household_stats', 'household_member_stats',
        # 주택 관련 테이블들
        'house_stats',
        # 사업체 관련 테이블들
        'company_stats',
        # 농림어업 관련 테이블들
        'farm_household_stats', 'forestry_household_stats', 'fishery_household_stats',
        # 산업분류 테이블
        'industry_code_stats',
        # SGIS API 기반 상세 테이블들 (향후 확장용)
        'main_population_stats', 'population_detail_stats', 'household_detail_stats',
        'house_detail_stats', 'company_detail_stats', 'industry_classification',
        'farm_household_detail', 'forestry_household_detail', 'fishery_household_detail'
    ]
    
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        SQL 쿼리 종합 검증
        
        Args:
            query: 검증할 SQL 쿼리
            
        Returns:
            Tuple[bool, Optional[str]]: (검증 성공 여부, 오류 메시지)
        """
        if not query or not query.strip():
            return False, "빈 쿼리입니다"
        
        query_upper = query.upper()
        
        # 1. 위험한 키워드 검사
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"금지된 SQL 키워드: {keyword}"
        
        # 2. SELECT 문만 허용 (주석 제거 후 검사)
        clean_query = self._remove_comments(query_upper).strip()
        if not clean_query.startswith('SELECT'):
            return False, "SELECT 문만 허용됩니다"
        
        # 3. 다중 쿼리 방지
        semicolon_count = query.count(';')
        if semicolon_count > 1:
            return False, "다중 쿼리는 금지되어 있습니다"
        elif semicolon_count == 1 and not query.strip().endswith(';'):
            return False, "다중 쿼리는 금지되어 있습니다"
        
        # 4. 테이블명 검증
        return self._validate_tables(query_upper)
    
    def _remove_comments(self, query: str) -> str:
        """SQL 주석 제거 (-- 및 /* */ 주석)"""
        # -- 주석 제거
        lines = query.split('\n')
        clean_lines = []
        for line in lines:
            comment_pos = line.find('--')
            if comment_pos != -1:
                line = line[:comment_pos]
            clean_lines.append(line)
        
        # /* */ 주석 제거
        query_no_line_comments = '\n'.join(clean_lines)
        query_no_comments = re.sub(r'/\*.*?\*/', '', query_no_line_comments, flags=re.DOTALL)
        
        return query_no_comments
    
    def _validate_tables(self, query_upper: str) -> Tuple[bool, Optional[str]]:
        """테이블명 유효성 검증"""
        # FROM 절에서 테이블명 추출
        table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query_upper)
        
        # JOIN 절에서 테이블명 추출
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_tables = re.findall(join_pattern, query_upper)
        tables.extend(join_tables)
        
        # 모든 테이블이 허용 목록에 있는지 확인
        for table in tables:
            if table.lower() not in [t.lower() for t in self.ALLOWED_TABLES]:
                return False, f"허용되지 않은 테이블: {table}"
        
        return True, None
    
    def get_query_complexity_score(self, query: str) -> int:
        """
        쿼리 복잡도 점수 계산 (0-10)
        
        Args:
            query: 분석할 SQL 쿼리
            
        Returns:
            int: 복잡도 점수 (높을수록 복잡)
        """
        score = 0
        query_upper = query.upper()
        
        # JOIN 개수
        score += len(re.findall(r'\bJOIN\b', query_upper)) * 2
        
        # 서브쿼리 개수
        score += len(re.findall(r'\bSELECT\b', query_upper)) - 1
        
        # 집계 함수 개수
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'GROUP BY']
        for func in agg_functions:
            score += len(re.findall(f'\\b{func}\\b', query_upper))
        
        # WHERE 조건 복잡도
        score += len(re.findall(r'\bAND\b|\bOR\b', query_upper))
        
        return min(score, 10)  # 최대 10점


# ===== SQL 실행기 =====

class SQLExecutor:
    """SQL 쿼리 실행기 - 검증된 쿼리만을 안전하게 실행"""
    
    def __init__(self, validator: SQLValidator, db_manager):
        """
        초기화
        
        Args:
            validator: SQL 검증기
            db_manager: 데이터베이스 매니저
        """
        self.validator = validator
        self.db_manager = db_manager
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """
        SQL 쿼리 실행
        
        Args:
            query: 실행할 SQL 쿼리
            
        Returns:
            Dict[str, Any]: 실행 결과
        """
        try:
            # 1. 쿼리 검증
            is_valid, error_msg = self.validator.validate(query)
            if not is_valid:
                logger.warning(f"🚫 SQL 검증 실패: {error_msg}")
                return {
                    "success": False,
                    "result": f"쿼리 검증 실패: {error_msg}",
                    "error": error_msg,
                    "query": query
                }
            
            # 2. 복잡도 검사
            complexity = self.validator.get_query_complexity_score(query)
            if complexity > 8:
                logger.warning(f"⚠️ 높은 복잡도 쿼리 (점수: {complexity}): {query[:100]}...")
            
            # 3. 쿼리 실행
            async with self.db_manager.get_async_session() as session:
                db_service = DatabaseService(session)
                results = await db_service.execute_raw_query(query)
            
            # 4. 결과 처리
            if results is None:
                logger.warning("⚠️ SQL 실행 결과가 None입니다")
                return {
                    "success": False,
                    "result": "SQL 실행 결과를 가져올 수 없습니다",
                    "error": "No results",
                    "query": query
                }
            
            if not results:
                logger.info("ℹ️ SQL 실행 성공 - 결과 없음")
                return {
                    "success": True,
                    "result": "쿼리가 성공적으로 실행되었으나 결과가 없습니다.",
                    "row_count": 0,
                    "query": query
                }
            
            # 5. 성공 결과 반환
            formatted_result = self._format_results(results)
            logger.info(f"✅ SQL 실행 성공 - {len(results)}개 행 반환")
            
            return {
                "success": True,
                "result": formatted_result,
                "row_count": len(results),
                "complexity_score": complexity,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"❌ SQL Executor 오류: {e}")
            logger.error(f"🔍 실패 쿼리: {query}")
            return {
                "success": False,
                "result": f"데이터베이스 실행 중 오류발생: {str(e)}",
                "error": str(e),
                "query": query
            }
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        쿼리 결과를 사용자 친화적인 테이블 형태로 포맷팅
        
        Args:
            results: 쿼리 실행 결과
            
        Returns:
            str: 포맷된 결과 문자열
        """
        if not results:
            return "쿼리 결과가 없습니다."
        
        if not isinstance(results, list):
            return f"결과: {results}"
        
        try:
            headers = list(results[0].keys())
            table_lines = []
            
            # 헤더 생성
            header_line = " | ".join(str(h) for h in headers)
            table_lines.append(header_line)
            table_lines.append("-" * len(header_line))
            
            # 데이터 행 추가 (최대 50행)
            max_rows = min(50, len(results))
            for i in range(max_rows):
                row = results[i]
                # 숫자 데이터 포맷팅 (천단위 콤마)
                formatted_values = []
                for h in headers:
                    value = row.get(h, "")
                    if isinstance(value, (int, float)) and value > 999:
                        formatted_values.append(f"{value:,}")
                    else:
                        formatted_values.append(str(value))
                
                row_line = " | ".join(formatted_values)
                table_lines.append(row_line)
            
            if len(results) > max_rows:
                table_lines.append(f"... (총 {len(results)}개 중 {max_rows}개만 표시)")
            
            return f"쿼리 실행 결과 ({len(results)}개 행):\n\n" + "\n".join(table_lines)
            
        except Exception as e:
            return f"결과 포맷팅 오류: {str(e)}, 원본 결과: {results[:3]}..."


# ===== SQL 생성기 =====

class SQLGenerator:
    """LLM을 활용한 SQL 쿼리 생성기"""
    
    def __init__(self, llm):
        """
        초기화
        
        Args:
            llm: 언어 모델 인스턴스
        """
        self.llm = llm
    
    async def generate(self, question: str, schema_info: str = "") -> str:
        """
        자연어 질문을 SQL 쿼리로 변환
        
        Args:
            question: 사용자 질문
            schema_info: 데이터베이스 스키마 정보
            
        Returns:
            str: 생성된 SQL 쿼리
        """
        try:
            # 지역정보 추출 및 매핑
            region_info = self._extract_region_info(question)
            
            # 프롬프트 템플릿 생성
            prompt_text = get_sql_generation_prompt(
                question=question,
                region_info=region_info,
                schema_info=schema_info or get_database_schema()
            )
            
            prompt = ChatPromptTemplate.from_template(prompt_text)
            chain = prompt | self.llm
            
            result = await chain.ainvoke({
                "question": question,
                "schema_info": schema_info or get_database_schema(),
                "region_info": region_info
            })
            
            return self._extract_sql(result.content)
            
        except Exception as e:
            logger.error(f"SQL 생성 오류: {e}")
            return f"-- 오류: SQL 생성 실패 - {str(e)}"
    
    def _extract_sql(self, llm_response: str) -> str:
        """LLM 응답에서 실제 SQL 쿼리 추출"""
        lines = llm_response.split('\n')
        sql_lines = []
        in_sql_block = False
        
        # 코드 블록에서 SQL 추출
        for line in lines:
            line = line.strip()
            
            if line.startswith('```sql'):
                in_sql_block = True
                continue
            elif line.startswith('```') and in_sql_block:
                break
            elif in_sql_block and line:
                sql_lines.append(line)
        
        # 대안 방법: SELECT로 시작하는 줄 찾기
        if not sql_lines:
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SELECT'):
                    sql_lines.append(line)
                    # 다음 줄들도 SQL의 일부인지 확인
                    idx = lines.index(line.strip())
                    for next_line in lines[idx+1:]:
                        next_line = next_line.strip()
                        if next_line and not next_line.startswith('#') and not next_line.startswith('--'):
                            if any(keyword in next_line.upper() for keyword in ['FROM', 'WHERE', 'ORDER', 'GROUP', 'LIMIT', 'JOIN']):
                                sql_lines.append(next_line)
                            else:
                                break
                        elif next_line.endswith(';'):
                            sql_lines.append(next_line)
                            break
                    break
        
        return '\n'.join(sql_lines) if sql_lines else "SELECT 1; -- 생성 실패"
    
    def _extract_region_info(self, question: str) -> str:
        """질문에서 지역 정보 추출 및 매핑"""
        regions = []
        
        # 지역명 매핑 사전
        region_mapping = {
            # 광역시도
            "서울": ("서울특별시", "11"),
            "부산": ("부산광역시", "47"), 
            "대구": ("대구광역시", "27"),
            "인천": ("인천광역시", "28"),
            "광주": ("광주광역시", "29"),
            "대전": ("대전광역시", "30"),
            "울산": ("울산광역시", "31"),
            "세종": ("세종특별자치시", "36"),
            "경기": ("경기도", "41"),
            "강원": ("강원특별자치도", "42"),
            "충북": ("충청북도", "43"),
            "충남": ("충청남도", "44"),
            "전북": ("전북특별자치도", "45"),
            "전남": ("전라남도", "46"),
            "경북": ("경상북도", "47"),
            "경남": ("경상남도", "48"),
            "제주": ("제주특별자치도", "50"),
            
            # 부산 구별 (예시)
            "해운대": ("해운대구", "47111"),
            "수영": ("수영구", "47113"),
            "사하": ("사하구", "47115"),
            "금정": ("금정구", "47118"),
        }
        
        # 질문에서 지역명 찾기
        for region_key, (full_name, code) in region_mapping.items():
            if region_key in question:
                regions.append(f"{full_name} (adm_cd: '{code}')")
        
        # 비교 키워드 감지
        comparison_keywords = ["비교", "vs", "대비", "차이", "순위", "많은", "적은"]
        is_comparison = any(keyword in question for keyword in comparison_keywords)
        
        if regions:
            result = f"감지된 지역: {', '.join(regions)}"
            if is_comparison and len(regions) >= 2:
                result += "\n💡 비교 분석: 여러 지역 간의 비교 분석 쿼리"
            return result
        else:
            return "지역 정보가 명시되지 않음 - 전국 또는 특정 지역 코드를 사용해 검색"


# ===== LangChain Tool 래퍼 =====

@tool
async def execute_sql_query(query: str) -> str:
    """
    SQL 쿼리 실행 도구
    
    한국 통계청 데이터베이스에서 안전하게 SQL을 실행합니다.
    SELECT 문만 허용되며, 결과는 테이블 형태로 반환됩니다.
    
    Args:
        query: 실행할 SQL 쿼리 (SELECT 문만 허용)
        
    Returns:
        str: 실행 결과 또는 오류 메시지
    """
    from .container import get_service
    
    try:
        executor = await get_service("sql_executor")
        result = await executor.execute(query)
        
        if result["success"]:
            return result["result"]
        else:
            return f"오류: {result['result']}"
            
    except Exception as e:
        logger.error(f"execute_sql_query 도구 오류: {e}")
        return f"도구 실행 오류: {str(e)}"


@tool 
async def get_database_schema_info() -> str:
    """
    데이터베이스 스키마 정보 조회 도구
    
    사용 가능한 테이블과 컬럼 정보를 반환합니다.
    
    Returns:
        str: 데이터베이스 스키마 정보
    """
    return get_database_schema()


@tool
async def validate_sql_query(query: str) -> str:
    """
    SQL 쿼리 검증 도구
    
    SQL 쿼리의 안전성과 유효성을 검증합니다.
    
    Args:
        query: 검증할 SQL 쿼리
        
    Returns:
        str: 검증 결과
    """
    validator = SQLValidator()
    is_valid, error_msg = validator.validate(query)
    
    if is_valid:
        complexity = validator.get_query_complexity_score(query)
        return f"✅ 쿼리 검증 성공 (복잡도: {complexity}/10)"
    else:
        return f"❌ 쿼리 검증 실패: {error_msg}"


# ===== 사용 가능한 도구 목록 =====

AVAILABLE_TOOLS = [
    execute_sql_query,
    get_database_schema_info, 
    validate_sql_query
]


# ===== 도구 설정 정보 =====

TOOL_DESCRIPTIONS = {
    "execute_sql_query": "한국 통계청 데이터에서 SQL 쿼리를 안전하게 실행",
    "get_database_schema_info": "사용 가능한 데이터베이스 테이블과 컬럼 정보 조회",
    "validate_sql_query": "SQL 쿼리의 안전성과 유효성 검증"
}


def get_tool_by_name(tool_name: str):
    """도구 이름으로 도구 인스턴스 반환"""
    tool_map = {tool.name: tool for tool in AVAILABLE_TOOLS}
    return tool_map.get(tool_name)