"""
Agent 도구 정의
SQL 쿼리 실행 도구와 관련 유틸리티
"""
import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.tools import tool
from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import get_database_manager
from src.database.repository import DatabaseService


logger = logging.getLogger(__name__)


class SQLQueryValidator:
    """SQL 쿼리 검증기"""
    
    # 위험한 키워드들
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE'
    ]
    
    # 허용된 테이블들
    ALLOWED_TABLES = [
        'population_stats', 'population_search_stats', 'household_stats', 'house_stats', 
        'company_stats', 'farm_household_stats', 'forestry_household_stats', 
        'fishery_household_stats', 'household_member_stats', 'industry_code_stats'
    ]
    
    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, Optional[str]]:
        """쿼리 검증"""
        # 기본 검증
        if not query or not query.strip():
            return False, "빈 쿼리입니다"
        
        query_upper = query.upper()
        
        # 위험한 키워드 검사
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"허용되지 않은 키워드가 포함되어 있습니다: {keyword}"
        
        # SELECT 문인지 확인
        if not query_upper.strip().startswith('SELECT'):
            return False, "SELECT 문만 허용됩니다"
        
        # 세미콜론 개수 확인 (다중 쿼리 방지)
        if query.count(';') > 1:
            return False, "다중 쿼리는 허용되지 않습니다"
        
        # 테이블 이름 검증
        table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query_upper)
        
        for table in tables:
            if table.lower() not in cls.ALLOWED_TABLES:
                return False, f"허용되지 않은 테이블입니다: {table}"
        
        # JOIN에 사용된 테이블도 검증
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_tables = re.findall(join_pattern, query_upper)
        
        for table in join_tables:
            if table.lower() not in cls.ALLOWED_TABLES:
                return False, f"허용되지 않은 테이블입니다: {table}"
        
        return True, None


@tool
async def execute_sql_query(query: str) -> str:
    """
    SQL 쿼리를 실행하고 결과를 반환합니다.
    
    Args:
        query: 실행할 SQL 쿼리 (SELECT 문만 허용)
    
    Returns:
        쿼리 실행 결과를 문자열로 반환
    """
    try:
        # 쿼리 검증
        is_valid, error_msg = SQLQueryValidator.validate_query(query)
        if not is_valid:
            return f"쿼리 검증 실패: {error_msg}"
        
        # 쿼리 실행
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            results = await db_service.execute_raw_query(query)
        
        # 결과 포맷팅
        if not results:
            return "쿼리 결과가 없습니다."
        
        # 결과를 테이블 형태로 포맷팅
        if len(results) > 0:
            # 컬럼 헤더
            headers = list(results[0].keys())
            
            # 테이블 생성
            table_lines = []
            
            # 헤더 라인
            header_line = " | ".join(str(h) for h in headers)
            table_lines.append(header_line)
            table_lines.append("-" * len(header_line))
            
            # 데이터 라인들 (최대 50개 행만 표시)
            max_rows = min(50, len(results))
            for i in range(max_rows):
                row = results[i]
                row_line = " | ".join(str(row.get(h, "")) for h in headers)
                table_lines.append(row_line)
            
            # 더 많은 결과가 있는 경우 메시지 추가
            if len(results) > max_rows:
                table_lines.append(f"... ({len(results) - max_rows}개 행 더 있음)")
            
            result_text = "\n".join(table_lines)
            return f"쿼리 실행 완료 ({len(results)}개 행):\n\n{result_text}"
        
        return "결과가 없습니다."
        
    except SQLAlchemyError as e:
        logger.error(f"SQL 실행 오류: {str(e)}")
        return f"SQL 실행 오류: {str(e)}"
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        return f"오류가 발생했습니다: {str(e)}"


@tool
async def get_table_info(table_name: str) -> str:
    """
    테이블의 스키마 정보를 조회합니다.
    
    Args:
        table_name: 조회할 테이블 이름
    
    Returns:
        테이블 스키마 정보
    """
    try:
        if table_name not in SQLQueryValidator.ALLOWED_TABLES:
            return f"허용되지 않은 테이블입니다: {table_name}"
        
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            schema_info = await db_service.get_table_schema(table_name)
        
        if not schema_info:
            return f"테이블 '{table_name}'을 찾을 수 없습니다."
        
        # 스키마 정보 포맷팅
        lines = [f"테이블: {table_name}", ""]
        
        for column in schema_info:
            col_name = column['column_name']
            data_type = column['data_type']
            is_nullable = column['is_nullable']
            default_value = column['column_default']
            
            nullable_text = "NULL 허용" if is_nullable == 'YES' else "NOT NULL"
            default_text = f", 기본값: {default_value}" if default_value else ""
            
            lines.append(f"- {col_name}: {data_type} ({nullable_text}{default_text})")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"테이블 정보 조회 오류: {str(e)}")
        return f"테이블 정보 조회 중 오류가 발생했습니다: {str(e)}"


@tool
async def get_available_tables() -> str:
    """
    사용 가능한 모든 테이블 목록을 반환합니다.
    
    Returns:
        테이블 목록과 간단한 설명
    """
    try:
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            tables = await db_service.get_all_tables()
        
        # 테이블 설명 매핑
        table_descriptions = {
            'population_stats': '총조사 주요지표 (2015-2023)',
            'population_search_stats': '인구통계 데이터',
            'household_stats': '가구 통계 (2015-2023)',
            'house_stats': '주택 통계 (2015-2023)',
            'company_stats': '사업체 통계 (2000-2023)',
            'farm_household_stats': '농가 통계 (농림어업총조사)',
            'forestry_household_stats': '임가 통계 (농림어업총조사)',
            'fishery_household_stats': '어가 통계 (농림어업총조사)',
            'household_member_stats': '가구원 통계 (농림어업총조사)',
            'industry_code_stats': '산업분류별 통계 데이터'
        }
        
        lines = ["사용 가능한 테이블 목록:", ""]
        
        for table in sorted(tables):
            description = table_descriptions.get(table, "설명 없음")
            lines.append(f"- {table}: {description}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"테이블 목록 조회 오류: {str(e)}")
        return f"테이블 목록 조회 중 오류가 발생했습니다: {str(e)}"


@tool
async def search_administrative_area(search_term: str) -> str:
    """
    행정구역명으로 검색하여 행정구역코드를 찾습니다.
    
    Args:
        search_term: 검색할 행정구역명 (예: "포항", "서울", "강남구")
    
    Returns:
        검색 결과 (행정구역코드와 이름)
    """
    try:
        # 최신 연도 데이터에서 검색
        query = """
        SELECT DISTINCT adm_cd, adm_nm 
        FROM population_stats 
        WHERE year = 2023 
        AND adm_nm ILIKE %s
        ORDER BY LENGTH(adm_cd), adm_cd
        LIMIT 20
        """
        
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            results = await db_service.execute_raw_query(
                query.replace('%s', f"'%{search_term}%'")
            )
        
        if not results:
            return f"'{search_term}'와 일치하는 행정구역을 찾을 수 없습니다."
        
        lines = [f"'{search_term}' 검색 결과:", ""]
        
        for result in results:
            adm_cd = result['adm_cd']
            adm_nm = result['adm_nm']
            
            # 행정구역 레벨 판단
            if len(adm_cd) == 2:
                level = "시도"
            elif len(adm_cd) == 5:
                level = "시군구"
            elif len(adm_cd) == 8:
                level = "읍면동"
            else:
                level = "기타"
            
            lines.append(f"- {adm_cd}: {adm_nm} ({level})")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"행정구역 검색 오류: {str(e)}")
        return f"행정구역 검색 중 오류가 발생했습니다: {str(e)}"


@tool
async def semantic_search(query: str, limit: int = 5) -> str:
    """
    의미 검색을 통해 관련 통계 데이터나 문서를 찾습니다.
    
    Args:
        query: 검색할 질문이나 키워드
        limit: 반환할 결과 개수 (기본값: 5)
    
    Returns:
        유사한 문서들과 관련 정보
    """
    try:
        from langchain_openai import OpenAIEmbeddings
        from src.config.settings import get_settings
        
        settings = get_settings()
        
        # OpenAI 임베딩 생성
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key
        )
        
        # 쿼리를 임베딩으로 변환
        query_vector = await embeddings.aembed_query(query)
        
        # pgvector를 사용한 코사인 유사도 검색
        search_query = """
        SELECT 
            content,
            source_table,
            source_id,
            meta_data,
            1 - (embedding <=> %s::vector) as similarity
        FROM document_embeddings
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
        
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 벡터를 문자열로 변환
            vector_str = f"[{','.join(map(str, query_vector))}]"
            
            results = await db_service.execute_raw_query(
                search_query.replace('%s', '$1').replace('%s', '$2').replace('%s', '$3'),
                (vector_str, vector_str, limit)
            )
        
        if not results:
            return f"'{query}'와 관련된 문서를 찾을 수 없습니다. 먼저 create_embeddings_for_stats 도구를 사용해 데이터를 임베딩하세요."
        
        lines = [f"🔍 '{query}' 의미 검색 결과:", ""]
        
        for i, result in enumerate(results, 1):
            similarity = f"{result['similarity']:.3f}"
            content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
            
            lines.append(f"{i}. 유사도: {similarity}")
            lines.append(f"   내용: {content_preview}")
            lines.append(f"   출처: {result['source_table']} (ID: {result['source_id']})")
            
            # 메타데이터가 있으면 표시
            if result.get('meta_data'):
                meta_data = result['meta_data']
                if isinstance(meta_data, dict) and meta_data:
                    meta_info = []
                    for key, value in meta_data.items():
                        if value is not None:
                            meta_info.append(f"{key}: {value}")
                    if meta_info:
                        lines.append(f"   세부정보: {', '.join(meta_info[:3])}")  # 최대 3개만
            
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"의미 검색 오류: {str(e)}")
        return f"의미 검색 중 오류가 발생했습니다: {str(e)}"


@tool
async def create_embeddings_for_stats(year: int = 2023) -> str:
    """
    통계 데이터의 설명을 임베딩으로 변환하여 저장합니다.
    
    Args:
        year: 임베딩을 생성할 연도 (기본값: 2023)
    
    Returns:
        임베딩 생성 결과
    """
    try:
        from langchain_openai import OpenAIEmbeddings
        from src.config.settings import get_settings
        
        settings = get_settings()
        
        # OpenAI 임베딩 클라이언트 설정
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key
        )
        
        # 통계 데이터 요약 정보 조회
        summary_query = """
        SELECT 
            CONCAT('stats_', adm_cd, '_', year) as record_id,
            adm_cd,
            adm_nm,
            year,
            tot_ppltn,
            avg_age,
            ppltn_dnsty,
            male_ppltn,
            female_ppltn,
            CONCAT(
                adm_nm, ' ', year, '년 통계: ',
                '총인구 ', COALESCE(tot_ppltn::text, '정보없음'), '명, ',
                '평균연령 ', COALESCE(avg_age::text, '정보없음'), '세, ',
                '인구밀도 ', COALESCE(ppltn_dnsty::text, '정보없음'), '명/㎢, ',
                '남성 ', COALESCE(male_ppltn::text, '정보없음'), '명, ',
                '여성 ', COALESCE(female_ppltn::text, '정보없음'), '명'
            ) as description
        FROM population_stats 
        WHERE year = %s
        AND tot_ppltn IS NOT NULL
        ORDER BY adm_cd
        """
        
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            stats = await db_service.execute_raw_query(summary_query, (year,))
        
        if not stats:
            return f"{year}년 통계 데이터를 찾을 수 없습니다."
        
        embedded_count = 0
        error_count = 0
        
        # 배치로 임베딩 생성 (속도 향상)
        descriptions = [stat['description'] for stat in stats]
        
        try:
            # 임베딩 배치 생성
            embedding_vectors = await embeddings.aembed_documents(descriptions)
            
            # 각 통계 데이터에 대해 임베딩 저장
            for stat, embedding_vector in zip(stats, embedding_vectors):
                try:
                    # 메타데이터 구성
                    metadata = {
                        'year': stat['year'],
                        'total_population': stat['tot_ppltn'],
                        'avg_age': stat['avg_age'],
                        'population_density': stat['ppltn_dnsty'],
                        'male_population': stat['male_ppltn'],
                        'female_population': stat['female_ppltn']
                    }
                    
                    # 벡터를 문자열로 변환
                    vector_str = f"[{','.join(map(str, embedding_vector))}]"
                    
                    # DB에 저장 (UPSERT)
                    upsert_query = """
                    INSERT INTO document_embeddings (content, source_table, source_id, meta_data, embedding)
                    VALUES (%s, 'population_stats', %s, %s, %s::vector)
                    ON CONFLICT (source_table, source_id) 
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        meta_data = EXCLUDED.meta_data,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    
                    await db_service.execute_raw_query(
                        upsert_query,
                        (
                            stat['description'],
                            stat['record_id'],
                            metadata,
                            vector_str
                        )
                    )
                    embedded_count += 1
                    
                except Exception as e:
                    logger.error(f"개별 임베딩 저장 오류 (ID: {stat['record_id']}): {e}")
                    error_count += 1
                    continue
            
        except Exception as e:
            logger.error(f"배치 임베딩 생성 오류: {e}")
            return f"임베딩 생성 중 오류가 발생했습니다: {str(e)}"
        
        result_msg = f"✅ {year}년 통계 데이터 {embedded_count}개의 임베딩을 생성했습니다."
        if error_count > 0:
            result_msg += f"\n⚠️  {error_count}개 레코드에서 오류가 발생했습니다."
        
        return result_msg
        
    except Exception as e:
        logger.error(f"임베딩 생성 오류: {str(e)}")
        return f"임베딩 생성 중 오류가 발생했습니다: {str(e)}"


@tool
async def get_embedding_stats() -> str:
    """
    현재 저장된 임베딩 통계를 조회합니다.
    
    Returns:
        임베딩 데이터베이스 현황
    """
    try:
        stats_query = """
        SELECT 
            source_table,
            COUNT(*) as total_count,
            COUNT(embedding) as embedded_count,
            MIN(created_at) as oldest_created,
            MAX(updated_at) as latest_updated
        FROM document_embeddings
        GROUP BY source_table
        ORDER BY total_count DESC
        """
        
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            results = await db_service.execute_raw_query(stats_query)
        
        if not results:
            return "저장된 임베딩 데이터가 없습니다."
        
        lines = ["📊 임베딩 데이터베이스 현황:", ""]
        
        total_records = 0
        total_embedded = 0
        
        for result in results:
            source = result['source_table']
            total = result['total_count']
            embedded = result['embedded_count']
            oldest = result['oldest_created']
            latest = result['latest_updated']
            
            total_records += total
            total_embedded += embedded
            
            completion_rate = (embedded / total * 100) if total > 0 else 0
            
            lines.append(f"🗂️  {source}:")
            lines.append(f"   - 총 레코드: {total:,}개")
            lines.append(f"   - 임베딩 완료: {embedded:,}개 ({completion_rate:.1f}%)")
            lines.append(f"   - 생성일: {oldest.strftime('%Y-%m-%d') if oldest else 'N/A'}")
            lines.append(f"   - 최종 업데이트: {latest.strftime('%Y-%m-%d %H:%M') if latest else 'N/A'}")
            lines.append("")
        
        # 전체 요약
        overall_completion = (total_embedded / total_records * 100) if total_records > 0 else 0
        lines.append("📈 전체 요약:")
        lines.append(f"   - 총 레코드: {total_records:,}개")
        lines.append(f"   - 임베딩 완료: {total_embedded:,}개 ({overall_completion:.1f}%)")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"임베딩 통계 조회 오류: {str(e)}")
        return f"임베딩 통계 조회 중 오류가 발생했습니다: {str(e)}"


# 사용 가능한 도구들
AVAILABLE_TOOLS = [
    execute_sql_query,
    get_table_info,
    get_available_tables,
    search_administrative_area,
    semantic_search,
    create_embeddings_for_stats,
    get_embedding_stats,
]