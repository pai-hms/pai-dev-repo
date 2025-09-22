"""
Database Service Factory - DI Container 순환 참조 해결용
"""
from typing import Callable
from contextlib import AbstractContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from .service import DatabaseService, create_database_service


# 전역 서비스 인스턴스 캐시
_database_service: DatabaseService = None


async def get_database_service() -> DatabaseService:
    """
    데이터베이스 서비스 인스턴스 반환 - DI 컨테이너 없이 직접 생성
    순환 import를 방지하기 위해 container를 거치지 않음
    """
    global _database_service
    
    if _database_service is None:
        # Container 대신 직접 SessionFactory 생성
        from .session_factory import DatabaseSessionFactory
        from .settings import get_database_settings
        
        settings = get_database_settings()
        session_factory_instance = DatabaseSessionFactory(settings)
        
        # 세션 팩토리 함수 생성
        session_factory = session_factory_instance.get_session
        
        # DatabaseService 인스턴스 생성
        _database_service = create_database_service(session_factory)
    
    return _database_service


def reset_database_service():
    """데이터베이스 서비스 인스턴스 리셋 (테스트용)"""
    global _database_service
    _database_service = None
