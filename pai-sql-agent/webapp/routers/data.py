import logging
from fastapi import APIRouter

from webapp.models import HealthResponse
from src.database.service import get_database_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인 - DI 기반"""
    try:
        # 데이터베이스 연결 확인
        db_connected = False
        try:
            db_service = await get_database_service()
            # 간단한 쿼리로 연결 확인
            result = await db_service.execute_custom_query("SELECT 1 as test")
            db_connected = result.success
        except Exception as e:
            logger.warning(f"데이터베이스 연결 확인 실패: {e}")
            db_connected = False
        
        status = "healthy" if db_connected else "degraded"
        
        return HealthResponse(
            status=status,
            database_connected=db_connected
        )
        
    except Exception as e:
        logger.error(f"헬스체크 오류: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False
        )


@router.get("/database-info")
async def get_database_info():
    """데이터베이스 전체 정보 조회 - DI 기반"""
    try:
        db_service = await get_database_service()
        
        # 테이블 목록과 레코드 수 조회
        tables_info = []
        tables = await db_service.get_all_tables()
        
        for table_name in tables:
            try:
                # 레코드 수 조회
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = await db_service.execute_custom_query(count_query)
                row_count = count_result.data[0]['count'] if count_result.success and count_result.data else 0
                
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
            SELECT adm_cd, adm_nm, year, tot_ppltn as population 
            FROM population_stats 
            WHERE year = 2023 
            ORDER BY tot_ppltn DESC 
            LIMIT 5
            """
            sample_result = await db_service.execute_custom_query(sample_query)
            
            if sample_result.success and sample_result.data:
                sample_data = "최신 인구 통계 (2023년):\n"
                for row in sample_result.data:
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