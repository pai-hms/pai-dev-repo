"""
SQL 도구 유틸리티
SQL 관련 공통 기능 제공
"""
from typing import List, Dict, Any, Optional, Tuple
import re
import json
from datetime import datetime

from src.database.repository import SQLQueryValidator


class SQLResultFormatter:
    """SQL 결과 포맷터"""
    
    @staticmethod
    def format_as_table(results: List[Dict[str, Any]], max_rows: int = 50) -> str:
        """결과를 테이블 형태로 포맷팅"""
        if not results:
            return "결과가 없습니다."
        
        # 컬럼 헤더
        headers = list(results[0].keys())
        
        # 컬럼 너비 계산
        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
            for row in results[:max_rows]:
                value_len = len(str(row.get(header, "")))
                col_widths[header] = max(col_widths[header], value_len)
        
        # 테이블 생성
        lines = []
        
        # 헤더 라인
        header_parts = []
        separator_parts = []
        for header in headers:
            width = min(col_widths[header], 20)  # 최대 너비 제한
            header_parts.append(f"{header:<{width}}")
            separator_parts.append("-" * width)
        
        lines.append(" | ".join(header_parts))
        lines.append(" | ".join(separator_parts))
        
        # 데이터 라인들
        for i, row in enumerate(results[:max_rows]):
            row_parts = []
            for header in headers:
                value = str(row.get(header, ""))
                width = min(col_widths[header], 20)
                # 너무 긴 값은 자르기
                if len(value) > width:
                    value = value[:width-3] + "..."
                row_parts.append(f"{value:<{width}}")
            lines.append(" | ".join(row_parts))
        
        # 더 많은 결과가 있는 경우
        if len(results) > max_rows:
            lines.append(f"... ({len(results) - max_rows}개 행 더 있음)")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_as_json(results: List[Dict[str, Any]], pretty: bool = True) -> str:
        """결과를 JSON 형태로 포맷팅"""
        if pretty:
            return json.dumps(results, ensure_ascii=False, indent=2, default=str)
        else:
            return json.dumps(results, ensure_ascii=False, default=str)
    
    @staticmethod
    def format_as_csv(results: List[Dict[str, Any]]) -> str:
        """결과를 CSV 형태로 포맷팅"""
        if not results:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
        return output.getvalue()


class SQLAnalyzer:
    """SQL 쿼리 분석기"""
    
    @staticmethod
    def extract_table_names(query: str) -> List[str]:
        """쿼리에서 테이블 이름 추출"""
        # FROM 절의 테이블들
        from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        from_tables = re.findall(from_pattern, query.upper())
        
        # JOIN 절의 테이블들
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_tables = re.findall(join_pattern, query.upper())
        
        # 중복 제거 후 반환
        all_tables = set(from_tables + join_tables)
        return [table.lower() for table in all_tables]
    
    @staticmethod
    def extract_columns(query: str) -> List[str]:
        """쿼리에서 컬럼 이름 추출 (간단한 버전)"""
        # SELECT와 FROM 사이의 컬럼들 추출
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(select_pattern, query.upper(), re.DOTALL)
        
        if not match:
            return []
        
        columns_str = match.group(1)
        
        # 간단한 컬럼 파싱 (복잡한 쿼리는 완벽하지 않음)
        columns = []
        for col in columns_str.split(','):
            col = col.strip()
            # AS 키워드 처리
            if ' AS ' in col.upper():
                col = col.split(' AS ')[-1].strip()
            # 함수나 연산 제거하고 컬럼명만 추출
            if '.' in col:
                col = col.split('.')[-1]
            
            columns.append(col.strip())
        
        return columns
    
    @staticmethod
    def get_query_type(query: str) -> str:
        """쿼리 타입 확인"""
        query_upper = query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        elif query_upper.startswith('CREATE'):
            return 'CREATE'
        elif query_upper.startswith('DROP'):
            return 'DROP'
        elif query_upper.startswith('ALTER'):
            return 'ALTER'
        else:
            return 'UNKNOWN'
    
    @staticmethod
    def estimate_complexity(query: str) -> str:
        """쿼리 복잡도 추정"""
        query_upper = query.upper()
        
        complexity_score = 0
        
        # JOIN 개수
        join_count = len(re.findall(r'\bJOIN\b', query_upper))
        complexity_score += join_count * 2
        
        # 서브쿼리 개수  
        subquery_count = query.count('(') - query.count(')')
        if subquery_count > 0:
            complexity_score += subquery_count * 3
        
        # 집계 함수 개수
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'GROUP BY']
        for func in agg_functions:
            if func in query_upper:
                complexity_score += 1
        
        # HAVING, ORDER BY, LIMIT 등
        advanced_clauses = ['HAVING', 'ORDER BY', 'LIMIT', 'OFFSET', 'UNION', 'INTERSECT', 'EXCEPT']
        for clause in advanced_clauses:
            if clause in query_upper:
                complexity_score += 1
        
        if complexity_score <= 2:
            return 'SIMPLE'
        elif complexity_score <= 5:
            return 'MEDIUM'
        else:
            return 'COMPLEX'


class QueryBuilder:
    """쿼리 빌더 헬퍼"""
    
    @staticmethod
    def build_population_query(
        year: int,
        adm_cd: Optional[str] = None,
        adm_nm_like: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """인구 통계 쿼리 빌더"""
        
        # 기본 컬럼
        if not columns:
            columns = ['adm_cd', 'adm_nm', 'tot_ppltn', 'avg_age', 'ppltn_dnsty']
        
        query_parts = [
            f"SELECT {', '.join(columns)}",
            "FROM population_stats",
            f"WHERE year = {year}"
        ]
        
        if adm_cd:
            query_parts.append(f"AND adm_cd = '{adm_cd}'")
        
        if adm_nm_like:
            query_parts.append(f"AND adm_nm ILIKE '%{adm_nm_like}%'")
        
        query_parts.append("ORDER BY adm_cd")
        
        if limit:
            query_parts.append(f"LIMIT {limit}")
        
        return "\n".join(query_parts)
    
    @staticmethod
    def build_comparison_query(
        table: str,
        years: List[int],
        metric: str,
        adm_cd: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """연도별 비교 쿼리 빌더"""
        
        query_parts = [
            f"SELECT adm_cd, adm_nm, year, {metric}",
            f"FROM {table}",
            f"WHERE year IN ({', '.join(map(str, years))})"
        ]
        
        if adm_cd:
            query_parts.append(f"AND adm_cd = '{adm_cd}'")
        
        query_parts.append("ORDER BY adm_cd, year")
        
        if limit:
            query_parts.append(f"LIMIT {limit}")
        
        return "\n".join(query_parts)
    
    @staticmethod
    def build_ranking_query(
        table: str,
        year: int,
        metric: str,
        order: str = 'DESC',
        adm_level: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """랭킹 쿼리 빌더"""
        
        query_parts = [
            f"SELECT adm_cd, adm_nm, {metric}",
            f"FROM {table}",
            f"WHERE year = {year}",
            f"AND {metric} IS NOT NULL"
        ]
        
        # 행정구역 레벨 필터
        if adm_level == 'sido':
            query_parts.append("AND LENGTH(adm_cd) = 2")
        elif adm_level == 'sigungu':
            query_parts.append("AND LENGTH(adm_cd) = 5")
        elif adm_level == 'emd':
            query_parts.append("AND LENGTH(adm_cd) = 8")
        
        query_parts.extend([
            f"ORDER BY {metric} {order.upper()}",
            f"LIMIT {limit}"
        ])
        
        return "\n".join(query_parts)