"""
데이터베이스 리포지토리
데이터 주권 원칙에 따라 각 모델별 데이터 제어권을 담당
"""
from typing import List, Optional, Dict, Any, Type, Union
from datetime import datetime
from sqlalchemy import select, insert, update, delete, text, desc, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    Base, PopulationStats, PopulationSearchStats, HouseholdStats, HouseStats, CompanyStats,
    FarmHouseholdStats, ForestryHouseholdStats, FisheryHouseholdStats,
    HouseholdMemberStats, CrawlLog, IndustryCodeStats
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
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """대량 upsert (insert or update)"""
        if not data_list:
            return
        
        # PostgreSQL의 ON CONFLICT를 사용한 upsert
        stmt = pg_insert(self.model).values(data_list)
        
        # 중복 키 처리: 모든 컬럼 업데이트 (id, created_at 제외)
        excluded_columns = {
            col.name: stmt.excluded[col.name]
            for col in self.model.__table__.columns
            if col.name not in ['id', 'created_at']
        }
        
        # year와 adm_cd가 있는 모델들의 경우 이를 기준으로 conflict 처리
        if hasattr(self.model, 'year') and hasattr(self.model, 'adm_cd'):
            # 어가통계는 oga_div도 포함
            if hasattr(self.model, 'oga_div'):
                conflict_columns = ['year', 'adm_cd', 'oga_div']
            # 가구원통계는 모든 unique constraint 필드 포함
            elif hasattr(self.model, 'data_type') and hasattr(self.model, 'gender') and hasattr(self.model, 'age_from'):
                conflict_columns = ['year', 'adm_cd', 'data_type', 'gender', 'age_from', 'age_to']
            else:
                conflict_columns = ['year', 'adm_cd']
            
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_=excluded_columns
            )
        elif hasattr(self.model, 'industry_cd'):
            # 산업분류는 industry_cd 기준
            stmt = stmt.on_conflict_do_update(
                index_elements=['industry_cd'],
                set_=excluded_columns
            )
        else:
            # 기본적으로 모든 데이터를 새로 삽입 (conflict 무시)
            stmt = stmt.on_conflict_do_nothing()
        
        await self.session.execute(stmt)


class PopulationRepository(BaseRepository):
    """인구 통계 리포지토리 (총조사 주요지표)"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, PopulationStats)


class PopulationSearchRepository(BaseRepository):
    """인구통계 검색 리포지토리 (searchpopulation.json)"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, PopulationSearchStats)
    
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


class HouseRepository(BaseRepository):
    """주택 통계 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, HouseStats)
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """주택 통계 데이터 배치 업서트"""
        if not data_list:
            return
        
        for data in data_list:
            existing = await self.session.execute(
                select(HouseStats).where(
                    HouseStats.year == data["year"],
                    HouseStats.adm_cd == data["adm_cd"]
                )
            )
            existing_record = existing.scalar_one_or_none()
            
            if existing_record:
                for key, value in data.items():
                    if hasattr(existing_record, key):
                        setattr(existing_record, key, value)
            else:
                new_record = HouseStats(**data)
                self.session.add(new_record)


class IndustryCodeRepository(BaseRepository):
    """산업분류 통계 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, IndustryCodeStats)
    
    async def upsert_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """산업분류 통계 데이터 배치 업서트"""
        if not data_list:
            return
        
        for data in data_list:
            existing = await self.session.execute(
                select(IndustryCodeStats).where(
                    IndustryCodeStats.year == data["year"],
                    IndustryCodeStats.adm_cd == data["adm_cd"],
                    IndustryCodeStats.industry_cd == data.get("industry_cd")
                )
            )
            existing_record = existing.scalar_one_or_none()
            
            if existing_record:
                for key, value in data.items():
                    if hasattr(existing_record, key):
                        setattr(existing_record, key, value)
            else:
                new_record = IndustryCodeStats(**data)
                self.session.add(new_record)


class FarmHouseholdRepository(BaseRepository):
    """농가 통계 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, FarmHouseholdStats)


class ForestryHouseholdRepository(BaseRepository):
    """임가 통계 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ForestryHouseholdStats)


class FisheryHouseholdRepository(BaseRepository):
    """어가 통계 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, FisheryHouseholdStats)


class HouseholdMemberRepository(BaseRepository):
    """가구원 통계 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, HouseholdMemberStats)


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
        self.population_search = PopulationSearchRepository(session)
        self.household = HouseholdRepository(session)
        self.house = HouseRepository(session)
        self.company = CompanyRepository(session)
        self.industry = IndustryCodeRepository(session)
        self.farm_household = FarmHouseholdRepository(session)
        self.forestry_household = ForestryHouseholdRepository(session)
        self.fishery_household = FisheryHouseholdRepository(session)
        self.household_member = HouseholdMemberRepository(session)
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