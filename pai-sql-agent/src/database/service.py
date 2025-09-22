"""
Database Service Layer - 완전한 DI 기반 Repository 중심 아키텍처
Repository가 데이터 제어권을 담당하며, Service는 비즈니스 로직만 처리
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from contextlib import AbstractContextManager
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .repository import DatabaseRepository
from .domains import StatisticsData, QueryResult
from .session_factory import DatabaseSessionFactory
from .settings import get_database_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """데이터베이스 서비스 - 완전한 DI 기반 비즈니스 로직 담당"""
    
    def __init__(self, session_factory: Callable[[], AbstractContextManager[AsyncSession]]):
        """
        Args:
            session_factory: 세션 팩토리 함수 (DI로 주입됨)
        """
        self.session_factory = session_factory
        logger.info("DatabaseService 초기화 완료 (완전한 DI 기반)")
    
    async def get_population_by_region(self, region_name: str, year: int = 2023) -> Optional[StatisticsData]:
        """지역별 인구 조회"""
        try:
            async with self.session_factory() as session:
                # Repository가 데이터 제어권 담당
                repository = DatabaseRepository(session)
                
                query = """
                SELECT adm_cd, adm_nm, year, tot_ppltn as population
                FROM population_stats 
                WHERE adm_nm LIKE %s AND year = %s
                ORDER BY tot_ppltn DESC
                LIMIT 1
                """
                
                results = await repository.execute_raw_query(query)
                
                if results:
                    row = results[0]
                    return StatisticsData(
                        region_code=row['adm_cd'],
                        region_name=row['adm_nm'],
                        year=row['year'],
                        population=row['population']
                    )
                return None
                
        except Exception as e:
            logger.error(f"인구 조회 오류: {e}")
            return None
    
    async def get_top_regions_by_population(self, year: int = 2023, limit: int = 10) -> List[StatisticsData]:
        """인구 상위 지역 조회"""
        try:
            async with self.session_factory() as session:
                # Repository가 데이터 제어권 담당
                repository = DatabaseRepository(session)
                
                query = """
                SELECT adm_cd, adm_nm, year, tot_ppltn as population
                FROM population_stats 
                WHERE year = %s AND tot_ppltn IS NOT NULL
                ORDER BY tot_ppltn DESC
                LIMIT %s
                """
                
                results = await repository.execute_raw_query(query)
                
                return [
                    StatisticsData(
                        region_code=row['adm_cd'],
                        region_name=row['adm_nm'],
                        year=row['year'],
                        population=row['population']
                    )
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"상위 지역 조회 오류: {e}")
            return []
    
    async def execute_custom_query(self, query: str) -> QueryResult:
        """사용자 정의 쿼리 실행"""
        start_time = datetime.now()
        
        try:
            async with self.session_factory() as session:
                # Repository가 데이터 제어권 담당
                repository = DatabaseRepository(session)
                results = await repository.execute_raw_query(query)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return QueryResult(
                    success=True,
                    data=results,
                    row_count=len(results) if results else 0,
                    execution_time=execution_time,
                    query=query
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"쿼리 실행 오류: {e}")
            return QueryResult(
                success=False,
                data=[],
                row_count=0,
                error=str(e),
                execution_time=execution_time,
                query=query
            )
    
    async def get_all_tables(self) -> List[str]:
        """모든 테이블 목록 조회 - Repository에 위임"""
        try:
            async with self.session_factory() as session:
                repository = DatabaseRepository(session)
                return await repository.get_all_tables()
        except Exception as e:
            logger.error(f"테이블 목록 조회 오류: {e}")
            return []


# DI 기반 서비스 팩토리 함수들
def create_database_service(session_factory: Callable[[], AbstractContextManager[AsyncSession]]) -> DatabaseService:
    """데이터베이스 서비스 팩토리 함수 (DI용)"""
    return DatabaseService(session_factory)


# 직접 생성 함수 - Container 의존성 없음
async def get_database_service() -> DatabaseService:
    """
    데이터베이스 서비스 인스턴스 반환 - 직접 생성 방식
    매번 새로운 인스턴스를 생성하여 순환 참조 완전 차단
    """
    settings = get_database_settings()
    session_factory_instance = DatabaseSessionFactory(settings)
    
    # 세션 팩토리 함수 생성
    session_factory = session_factory_instance.get_session
    
    # 매번 새로운 DatabaseService 인스턴스 생성
    return create_database_service(session_factory)
