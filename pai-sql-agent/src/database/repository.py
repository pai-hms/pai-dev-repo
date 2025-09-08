"""
데이터베이스 리포지토리
데이터 주권 원칙에 따라 각 모델별 데이터 제어권을 담당
"""
from typing import List, Optional, Dict, Any, Type, Union
from datetime import datetime
from sqlalchemy import select, insert, update, delete, text, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    Base, PopulationStats, HouseholdStats, HouseStats, CompanyStats,
    FarmHouseholdStats, ForestryHouseholdStats, FisheryHouseholdStats,
    HouseholdMemberStats, CrawlLog
)


class BaseRepository:
    """기본 리포지토리 클래스"""
    
    def __init__(self, session: AsyncSession, model: Type[Base]):
        self.session = session
        self.model = model
    
    async def create(self, **kwargs) -> Base:
        """레코드 생성"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> None:
        """대량 레코드 생성"""
        if not data_list:
            return
        
        await self.session.execute(
            insert(self.model).values(data_list)
        )
    
    async def get_by_id(self, record_id: int) -> Optional[Base]:
        """ID로 레코드 조회"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Base]:
        """모든 레코드 조회"""
        query = select(self.model)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def delete_by_id(self, record_id: int) -> bool:
        """ID로 레코드 삭제"""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == record_id)
        )
        return result.rowcount > 0
    
    async def count(self) -> int:
        """레코드 개수 조회"""
        result = await self.session.execute(
            select(func.count(self.model.id))
        )
        return result.scalar()


class PopulationRepository(BaseRepository):
    """인구 통계 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, PopulationStats)
    
    async def get_by_year_and_adm(
        self, 
        year: int, 
        adm_cd: str
    ) -> Optional[PopulationStats]:
        """연도와 행정구역코드로 조회"""
        result = await self.session.execute(
            select(self.model).where(
                self.model.year == year,
                self.model.adm_cd == adm_cd
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_year(self, year: int) -> List[PopulationStats]:
        """연도별 조회"""
        result = await self.session.execute(
            select(self.model).where(self.model.year == year)
            .order_by(self.model.adm_cd)
        )
        return list(result.scalars().all())
    
    async def get_by_adm_name_like(
        self, 
        name_pattern: str,
        year: Optional[int] = None
    ) -> List[PopulationStats]:
        """행정구역명 패턴으로 검색"""
        query = select(self.model).where(
            self.model.adm_nm.like(f"%{name_pattern}%")
        )
        
        if year:
            query = query.where(self.model.year == year)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """배치 업서트 (존재하면 업데이트, 없으면 삽입)"""
        if not data_list:
            return
        
        for data in data_list:
            # 기존 레코드 확인
            existing = await self.get_by_year_and_adm(
                data["year"], data["adm_cd"]
            )
            
            if existing:
                # 업데이트
                await self.session.execute(
                    update(self.model)
                    .where(
                        self.model.year == data["year"],
                        self.model.adm_cd == data["adm_cd"]
                    )
                    .values(**data)
                )
            else:
                # 삽입
                await self.create(**data)


class HouseholdRepository(BaseRepository):
    """가구 통계 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, HouseholdStats)
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """배치 업서트"""
        if not data_list:
            return
        
        for data in data_list:
            existing = await self.session.execute(
                select(self.model).where(
                    self.model.year == data["year"],
                    self.model.adm_cd == data["adm_cd"]
                )
            )
            
            if existing.scalar_one_or_none():
                await self.session.execute(
                    update(self.model)
                    .where(
                        self.model.year == data["year"],
                        self.model.adm_cd == data["adm_cd"]
                    )
                    .values(**data)
                )
            else:
                await self.create(**data)


class CompanyRepository(BaseRepository):
    """사업체 통계 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, CompanyStats)
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """배치 업서트"""
        if not data_list:
            return
        
        for data in data_list:
            existing = await self.session.execute(
                select(self.model).where(
                    self.model.year == data["year"],
                    self.model.adm_cd == data["adm_cd"]
                )
            )
            
            if existing.scalar_one_or_none():
                await self.session.execute(
                    update(self.model)
                    .where(
                        self.model.year == data["year"],
                        self.model.adm_cd == data["adm_cd"]
                    )
                    .values(**data)
                )
            else:
                await self.create(**data)


class CrawlLogRepository(BaseRepository):
    """크롤링 로그 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, CrawlLog)
    
    async def log_success(
        self,
        api_endpoint: str,
        year: Optional[int] = None,
        adm_cd: Optional[str] = None,
        response_count: int = 0
    ) -> CrawlLog:
        """성공 로그 기록"""
        return await self.create(
            api_endpoint=api_endpoint,
            year=year,
            adm_cd=adm_cd,
            status="success",
            response_count=response_count
        )
    
    async def log_error(
        self,
        api_endpoint: str,
        error_message: str,
        year: Optional[int] = None,
        adm_cd: Optional[str] = None
    ) -> CrawlLog:
        """에러 로그 기록"""
        return await self.create(
            api_endpoint=api_endpoint,
            year=year,
            adm_cd=adm_cd,
            status="error",
            error_message=error_message
        )
    
    async def get_recent_logs(
        self, 
        limit: int = 100
    ) -> List[CrawlLog]:
        """최근 로그 조회"""
        result = await self.session.execute(
            select(self.model)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_error_logs(
        self, 
        limit: int = 50
    ) -> List[CrawlLog]:
        """에러 로그만 조회"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.status == "error")
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


class DatabaseService:
    """데이터베이스 서비스 (Facade 패턴)"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.population = PopulationRepository(session)
        self.household = HouseholdRepository(session)
        self.company = CompanyRepository(session)
        self.crawl_log = CrawlLogRepository(session)
    
    async def execute_raw_query(self, query: str) -> List[Dict[str, Any]]:
        """원시 SQL 쿼리 실행"""
        result = await self.session.execute(text(query))
        
        # 결과를 딕셔너리 리스트로 변환
        columns = result.keys()
        rows = result.fetchall()
        
        return [
            dict(zip(columns, row)) for row in rows
        ]
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블 스키마 정보 조회"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_name = :table_name
        ORDER BY ordinal_position
        """
        
        result = await self.session.execute(
            text(query), {"table_name": table_name}
        )
        
        columns = result.keys()
        rows = result.fetchall()
        
        return [dict(zip(columns, row)) for row in rows]
    
    async def get_all_tables(self) -> List[str]:
        """모든 테이블 목록 조회"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        result = await self.session.execute(text(query))
        return [row[0] for row in result.fetchall()]