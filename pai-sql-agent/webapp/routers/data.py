import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.models import HealthResponse
from src.database.connection import get_async_session
from src.database.repository import DatabaseService
from src.crawler.sgis_client import SGISClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


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