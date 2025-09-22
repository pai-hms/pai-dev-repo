"""
Database Repository - SQL Agent
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """
    SQL Agent 전용 데이터베이스 리포지토리
    
    역할:
    - 원시 SQL 쿼리 실행 (Agent Tools용)
    - 스키마 정보 조회
    - 테이블 목록 조회
    
    Clean Architecture Infrastructure Layer
    """
    
    def __init__(self, session: AsyncSession):
        """
        생성자
        
        Args:
            session: SQLAlchemy 비동기 세션
        """
        self.session = session
    
    async def execute_raw_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        원시 SQL 쿼리 실행 - SQL Agent 도구용
        
        Args:
            query: 실행할 SQL 쿼리 문자열
            params: 쿼리 파라미터 (옵션)
            
        Returns:
            List[Dict[str, Any]]: 쿼리 결과를 딕셔너리 리스트로 반환
            
        Raises:
            Exception: 쿼리 실행 중 오류 발생 시
        """
        try:
            logger.info(f"원시 SQL 쿼리 실행: {query[:100]}...")
            
            # SQL 쿼리 실행 (파라미터 지원)
            if params:
                result = await self.session.execute(text(query), params)
            else:
                result = await self.session.execute(text(query))
            
            # 결과를 딕셔너리 리스트로 변환
            rows = result.fetchall()
            
            if not rows:
                logger.info("쿼리 결과: 데이터 없음")
                return []
            
            # 컬럼 이름과 함께 딕셔너리로 변환
            columns = result.keys()
            result_list = [
                {column: getattr(row, column) for column in columns}
                for row in rows
            ]
            
            logger.info(f"쿼리 실행 완료: {len(result_list)}개 행 반환")
            return result_list
            
        except Exception as e:
            logger.error(f"원시 SQL 쿼리 실행 오류: {e}")
            logger.error(f"실행한 쿼리: {query}")
            raise
    
    async def get_all_tables(self) -> List[str]:
        """
        모든 테이블 목록 조회
        
        Returns:
            List[str]: 테이블 이름 리스트
        """
        try:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            
            result = await self.session.execute(text(query))
            tables = [row[0] for row in result.fetchall()]
            
            logger.info(f"테이블 목록 조회 완료: {len(tables)}개 테이블")
            return tables
            
        except Exception as e:
            logger.error(f"테이블 목록 조회 오류: {e}")
            return []
    
    # get_table_schema, get_table_sample_data, get_database_statistics 메서드들 제거됨
    # 실제로는 execute_raw_query와 get_all_tables만 사용됨