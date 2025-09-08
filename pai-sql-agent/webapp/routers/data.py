import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
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
    """사용 가능한 테이블 목록을 반환합니다"""
    try:
        db_service = DatabaseService(session)
        tables = await db_service.get_all_tables()
        return tables
    except Exception as e:
        logger.error(f"테이블 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="테이블 목록 조회에 실패했습니다")


@router.get("/tables/{table_name}", response_model=TableInfoResponse)
async def get_table_info(
    table_name: str, 
    session: AsyncSession = Depends(get_async_session)
):
    """특정 테이블의 스키마 정보를 반환합니다"""
    try:
        db_service = DatabaseService(session)
        schema_info = await db_service.get_table_schema(table_name)
        
        if not schema_info:
            raise HTTPException(status_code=404, detail="테이블을 찾을 수 없습니다")
        
        # 테이블 설명 매핑
        descriptions = {
            'population_stats': '인구 통계 데이터 (2015-2023)',
            'household_stats': '가구 통계 데이터 (2015-2023)',
            'house_stats': '주택 통계 데이터 (2015-2023)',
            'company_stats': '사업체 통계 데이터 (2000-2023)',
            'farm_household_stats': '농가 통계 데이터',
            'forestry_household_stats': '임가 통계 데이터',
            'fishery_household_stats': '어가 통계 데이터',
            'household_member_stats': '가구원 통계 데이터',
            'crawl_logs': '데이터 수집 로그'
        }
        
        return TableInfoResponse(
            table_name=table_name,
            columns=schema_info,
            description=descriptions.get(table_name, "설명 없음")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"테이블 정보 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="테이블 정보 조회에 실패했습니다")


@router.post("/search/admin-area", response_model=AdminAreaSearchResponse)
async def search_admin_area(
    request: AdminAreaSearchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """행정구역을 검색합니다"""
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
        logger.error(f"행정구역 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="행정구역 검색에 실패했습니다")


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """시스템 상태를 확인합니다"""
    try:
        # 데이터베이스 연결 확인
        db_connected = False
        try:
            db_service = DatabaseService(session)
            await db_service.execute_raw_query("SELECT 1")
            db_connected = True
        except:
            pass
        
        # SGIS API 연결 확인 (간단한 인증 테스트)
        sgis_connected = False
        try:
            sgis_client = SGISClient()
            # 토큰 획득만 시도
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
        logger.error(f"헬스체크 중 오류: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            sgis_api_connected=False
        )
