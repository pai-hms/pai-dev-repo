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
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        특정 테이블의 스키마 정보 조회
        
        Args:
            table_name: 조회할 테이블 이름
            
        Returns:
            List[Dict[str, Any]]: 컬럼 정보 리스트
        """
        try:
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = :table_name
            ORDER BY ordinal_position
            """
        
            result = await self.session.execute(text(query), {"table_name": table_name})
            columns = result.fetchall()
            
            schema_info = []
            for column in columns:
                schema_info.append({
                    "column_name": column[0],
                    "data_type": column[1],
                    "is_nullable": column[2],
                    "column_default": column[3],
                    "max_length": column[4]
                })
            
            logger.info(f"테이블 '{table_name}' 스키마 조회 완료: {len(schema_info)}개 컬럼")
            return schema_info
            
        except Exception as e:
            logger.error(f"테이블 '{table_name}' 스키마 조회 오류: {e}")
            return []
    
    async def get_table_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        테이블의 샘플 데이터 조회
        
        Args:
            table_name: 조회할 테이블 이름
            limit: 조회할 행 수 (기본값: 5)
            
        Returns:
            List[Dict[str, Any]]: 샘플 데이터
        """
        try:
            query = f"SELECT * FROM {table_name} LIMIT :limit"
            result = await self.session.execute(text(query), {"limit": limit})
            
            rows = result.fetchall()
            if not rows:
                return []
            
            columns = result.keys()
            sample_data = [
                {column: getattr(row, column) for column in columns}
                for row in rows
            ]
            
            logger.info(f"테이블 '{table_name}' 샘플 데이터 조회 완료: {len(sample_data)}개 행")
            return sample_data
            
        except Exception as e:
            logger.error(f"테이블 '{table_name}' 샘플 데이터 조회 오류: {e}")
            return []
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """
        데이터베이스 전체 통계 정보 조회
        
        Returns:
            Dict[str, Any]: 데이터베이스 통계 정보
        """
        try:
            # 테이블별 행 수 조회
            tables = await self.get_all_tables()
            table_stats = {}
            total_rows = 0
            
            for table_name in tables:
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    result = await self.session.execute(text(count_query))
                    row_count = result.scalar()
                    table_stats[table_name] = row_count
                    total_rows += row_count
                except Exception as e:
                    logger.warning(f"테이블 '{table_name}' 행 수 조회 실패: {e}")
                    table_stats[table_name] = 0
            
            statistics = {
                "total_tables": len(tables),
                "total_rows": total_rows,
                "table_statistics": table_stats,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"데이터베이스 통계 조회 완료: {len(tables)}개 테이블, {total_rows:,}개 행")
            return statistics
            
        except Exception as e:
            logger.error(f"데이터베이스 통계 조회 오류: {e}")
            return {
                "total_tables": 0,
                "total_rows": 0,
                "table_statistics": {},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }