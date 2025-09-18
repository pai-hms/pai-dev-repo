import logging
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.models import (
    TableInfoResponse, AdminAreaSearchRequest, 
    AdminAreaSearchResponse, HealthResponse
)
from src.database.connection import get_async_session
from src.database.repository import DatabaseService
from src.crawler.sgis_client import SGISClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/tables", response_model=List[str])
async def get_tables(session: AsyncSession = Depends(get_async_session)):
    """데이터베이스 테이블 목록 반환"""
    try:
        db_service = DatabaseService(session)
        tables = await db_service.get_all_tables()
        return tables
    except Exception as e:
        logger.error(f"테이블 목록 조회 오류: {str(e)}")
        return []  # 빈 목록 반환


@router.get("/tables/{table_name}", response_model=TableInfoResponse)
async def get_table_info(
    table_name: str, 
    session: AsyncSession = Depends(get_async_session)
):
    """특정 테이블의 스키마 정보 반환"""
    try:
        db_service = DatabaseService(session)
        schema_info = await db_service.get_table_schema(table_name)
        
        if not schema_info:
            logger.warning(f"테이블 '{table_name}'을 찾을 수 없음")
            # 빈 스키마 정보 반환
            return TableInfoResponse(
                table_name=table_name,
                columns=[],
                description="테이블을 찾을 수 없음"
            )
        
        # 테이블 설명 매핑
        descriptions = {
            'population_stats': '인구 주민등록 통계 (2015-2023)',
            'population_search_stats': '인구 검색 통계',
            'household_stats': '가구 현황 통계 (2015-2023)',
            'house_stats': '주택 현황 통계 (2015-2023)',
            'company_stats': '사업체 현황 통계 (2000-2023)',
            'farm_household_stats': '농가 현황 통계',
            'forestry_household_stats': '임가 현황 통계',
            'fishery_household_stats': '어가 현황 통계',
            'household_member_stats': '가구원 현황 통계',
            'industry_code_stats': '산업분류 코드 통계'
        }
        
        return TableInfoResponse(
            table_name=table_name,
            columns=schema_info,
            description=descriptions.get(table_name, "기타 통계")
        )
        
    except Exception as e:
        logger.error(f"테이블 정보 조회 오류: {str(e)}")
        # 오류 시 빈 스키마 정보 반환
        return TableInfoResponse(
            table_name=table_name,
            columns=[],
            description="테이블 정보 조회 중 오류발생"
        )


@router.post("/search/admin-area", response_model=AdminAreaSearchResponse)
async def search_admin_area(
    request: AdminAreaSearchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """행정구역 검색"""
    try:
        db_service = DatabaseService(session)
        
        # 행정구역 검색 쿼리
        query = """
        SELECT DISTINCT adm_cd, adm_nm 
        FROM population_stats 
        WHERE year = 2023 
        AND adm_nm ILIKE %s
        ORDER BY LENGTH(adm_cd), adm_cd
        LIMIT 20
        """
        
        search_pattern = f"%{request.search_term}%"
        results = await db_service.execute_raw_query(
            query.replace('%s', f"'{search_pattern}'")
        )
        
        # 결과 포맷팅
        formatted_results = []
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
            
            formatted_results.append({
                "adm_cd": adm_cd,
                "adm_nm": adm_nm,
                "level": level
            })
        
        return AdminAreaSearchResponse(results=formatted_results)
        
    except Exception as e:
        logger.error(f"행정구역 검색 오류: {str(e)}")
        # 빈 결과 반환
        return AdminAreaSearchResponse(results=[])


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """서비스 상태 확인"""
    try:
        # 데이터베이스 연결 확인
        db_connected = False
        try:
            db_service = DatabaseService(session)
            await db_service.execute_raw_query("SELECT 1")
            db_connected = True
        except:
            pass
        
        # SGIS API 연결 확인 (선택적 기능)
        sgis_connected = False
        try:
            sgis_client = SGISClient()
            # 간단한 연결 테스트
            await sgis_client._get_access_token()
            sgis_connected = True
        except:
            pass
        
        status = "healthy" if db_connected and sgis_connected else "degraded"
        
        return HealthResponse(
            status=status,
            database_connected=db_connected,
            sgis_api_connected=sgis_connected
        )
        
    except Exception as e:
        logger.error(f"헬스체크 오류: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            sgis_api_connected=False
        )


@router.get("/database-info")
async def get_database_info(session: AsyncSession = Depends(get_async_session)):
    """데이터베이스 전체 정보 조회"""
    try:
        db_service = DatabaseService(session)
        
        # 테이블 목록과 레코드 수 조회
        tables_info = []
        tables = await db_service.get_all_tables()
        
        for table_name in tables:
            try:
                # 레코드 수 조회
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = await db_service.execute_raw_query(count_query)
                row_count = count_result[0]['count'] if count_result else 0
                
                tables_info.append({
                    "table_name": table_name,
                    "row_count": row_count
                })
            except Exception as e:
                logger.warning(f"테이블 {table_name} 정보 조회 실패: {e}")
                tables_info.append({
                    "table_name": table_name,
                    "row_count": 0
                })
        
        # 샘플 데이터 조회 (population_stats 테이블)
        sample_data = ""
        try:
            sample_query = """
            SELECT adm_cd, adm_nm, year, population 
            FROM population_stats 
            WHERE year = 2023 
            ORDER BY population DESC 
            LIMIT 5
            """
            sample_results = await db_service.execute_raw_query(sample_query)
            
            if sample_results:
                sample_data = "최신 인구 통계 (2023년):\n"
                for row in sample_results:
                    sample_data += f"- {row['adm_nm']}: {row['population']:,}명\n"
        except Exception as e:
            logger.warning(f"샘플 데이터 조회 실패: {e}")
            sample_data = "샘플 데이터를 조회할 수 없습니다."
        
        return {
            "success": True,
            "tables": tables_info,
            "sample_data": sample_data,
            "total_tables": len(tables_info)
        }
        
    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "tables": [],
            "sample_data": "",
            "total_tables": 0
        }