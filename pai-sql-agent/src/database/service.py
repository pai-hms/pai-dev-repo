"""
Database Service Layer - 독립적 서비스 (순환참조 제거)
Repository 패턴 기반 데이터베이스 비즈니스 로직 처리
"""
import asyncio
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
    """데이터베이스 서비스 - 독립적 서비스 (순환참조 제거)"""
    
    def __init__(self, session_factory: Callable[[], AbstractContextManager[AsyncSession]]):
        """
        Args:
            session_factory: 세션 팩토리 함수
        """
        self.session_factory = session_factory
        logger.info("DatabaseService 초기화 완료 (독립적 서비스)")
    
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


# 싱글톤 인스턴스를 위한 전역 변수
_database_service: Optional[DatabaseService] = None
_database_lock = asyncio.Lock()


# DI 기반 서비스 팩토리 함수들
def create_database_service(session_factory: Callable[[], AbstractContextManager[AsyncSession]]) -> DatabaseService:
    """데이터베이스 서비스 팩토리 함수 (DI용)"""
    return DatabaseService(session_factory)


# 싱글톤 패턴으로 변경
async def get_database_service() -> DatabaseService:
    """
    데이터베이스 서비스 싱글톤 인스턴스 반환
    스레드 안전한 지연 초기화로 성능 최적화
    """
    global _database_service
    
    if _database_service is None:
        async with _database_lock:
            # Double-checked locking pattern
            if _database_service is None:
                logger.info("DatabaseService 싱글톤 인스턴스 생성 시작")
                
                settings = get_database_settings()
                session_factory_instance = DatabaseSessionFactory(settings)
                session_factory = session_factory_instance.get_session
                
                _database_service = create_database_service(session_factory)
                logger.info("DatabaseService 싱글톤 인스턴스 생성 완료")
    
    return _database_service


async def close_database_service():
    """데이터베이스 서비스 싱글톤 정리"""
    global _database_service
    async with _database_lock:
        if _database_service is not None:
            logger.info("DatabaseService 싱글톤 인스턴스 정리")
            _database_service = None
