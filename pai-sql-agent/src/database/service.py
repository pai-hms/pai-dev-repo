"""
Database Service Layer
데이터베이스 관련 비즈니스 로직을 처리
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .repository import DatabaseRepository
from .domains import StatisticsData, QueryResult

logger = logging.getLogger(__name__)


class DatabaseService:
    """데이터베이스 비즈니스 로직 서비스"""
    
    def __init__(self, database_manager):
        self.database_manager = database_manager
    
    async def execute_safe_query(self, query: str) -> QueryResult:
        """안전한 쿼리 실행 (SELECT만 허용)"""
        # SQL 인젝션 방지 및 SELECT만 허용
        if not self._is_safe_query(query):
            raise ValueError("Only SELECT queries are allowed")
        
        start_time = datetime.now()
        
        try:
            # DatabaseManager를 통한 세션 관리 및 쿼리 실행
            async with self.database_manager.get_async_session() as session:
                repository = DatabaseRepository(session)
                result = await repository.execute_raw_query(query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=result if result else [],
                total_count=len(result) if result else 0,
                execution_time=execution_time,
                query=query
            )
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def _is_safe_query(self, query: str) -> bool:
        """쿼리 안전성 검증"""
        query_upper = query.upper().strip()
        
        # SELECT로 시작하는지 확인
        if not query_upper.startswith('SELECT'):
            return False
        
        # 위험한 키워드 포함 여부 확인
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 
            'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False
        
        return True
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """테이블 정보 조회"""
        async with self.database_manager.get_async_session() as session:
            repository = DatabaseRepository(session)
            return await repository.get_table_schema(table_name)
    
    async def get_database_schema(self) -> Dict[str, Any]:
        """전체 데이터베이스 스키마 정보"""
        async with self.database_manager.get_async_session() as session:
            repository = DatabaseRepository(session)
            return await repository.get_database_info()


# ✅ 비동기 싱글톤 팩토리
_database_service = None

async def get_database_service() -> DatabaseService:
    """데이터베이스 서비스 인스턴스 반환 (비동기 싱글톤)"""
    global _database_service
    
    if _database_service is None:
        # ✅ 비동기 DI 컨테이너 사용
        from .container import get_database_service_from_container
        _database_service = await get_database_service_from_container()
    
    return _database_service


async def reset_database_service():
    """데이터베이스 서비스 리셋 (개발/테스트용)"""
    global _database_service
    _database_service = None
    
    # 컨테이너도 리셋
    from .container import reset_container
    await reset_container()
