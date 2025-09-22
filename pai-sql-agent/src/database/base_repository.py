"""
Base Repository Pattern - DI 기반 범용 Repository
제네릭과 추상 클래스를 활용한 현대적 Repository 패턴
"""
import abc
import logging
from typing import (
    TypeVar, Generic, List, Optional, Dict, Any, 
    Callable, Type
)
from contextlib import AbstractContextManager

from sqlalchemy import select, insert, update, delete, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .entities import Base
from .domains import QueryResult

logger = logging.getLogger(__name__)

# 제네릭 타입 정의
DomainKey = TypeVar('DomainKey')  # 도메인 키 타입 (예: int, str, UUID)
Domain = TypeVar('Domain')        # 도메인 객체 타입
Entity = TypeVar('Entity', bound=Base)  # 엔티티 타입


class BaseRepository(abc.ABC, Generic[DomainKey, Domain, Entity]):
    """기본 Repository 추상 클래스 - DI 기반"""
    
    entity_class: Type[Entity]  # 관리할 엔티티 클래스 (하위 클래스에서 정의)
    
    def __init__(self, session_factory: Callable[..., AbstractContextManager[AsyncSession]]):
        """
        Args:
            session_factory: 세션 팩토리 (DI로 주입됨)
        """
        self.session_factory = session_factory
    
    # ==================== 추상 메서드들 ====================
    
    @abc.abstractmethod
    def entity_to_domain(self, entity: Entity) -> Domain:
        """엔티티를 도메인 객체로 변환"""
        pass
    
    @abc.abstractmethod
    def domain_to_entity(self, domain: Domain) -> Entity:
        """도메인 객체를 엔티티로 변환"""
        pass
    
    @abc.abstractmethod
    def get_primary_key(self, domain: Domain) -> DomainKey:
        """도메인 객체에서 기본 키 추출"""
        pass
    
    @abc.abstractmethod
    def update_entity_from_domain(self, entity: Entity, domain: Domain) -> None:
        """도메인 객체로 엔티티 업데이트"""
        pass
    
    # ==================== CRUD 기본 메서드들 ====================
    
    async def create(self, domain: Domain) -> Domain:
        """새로운 엔티티 생성"""
        async with self.session_factory() as session:
            entity = self.domain_to_entity(domain)
            session.add(entity)
            await session.flush()  # ID 생성을 위해 flush
            await session.refresh(entity)  # 최신 상태로 새로고침
            return self.entity_to_domain(entity)
    
    async def bulk_create(self, domains: List[Domain]) -> List[Domain]:
        """대량 엔티티 생성"""
        if not domains:
            return []
        
        async with self.session_factory() as session:
            entities = [self.domain_to_entity(domain) for domain in domains]
            session.add_all(entities)
            await session.flush()
            
            # 생성된 엔티티들을 도메인으로 변환
            return [self.entity_to_domain(entity) for entity in entities]
    
    async def get_by_id(self, key: DomainKey) -> Optional[Domain]:
        """기본 키로 엔티티 조회"""
        async with self.session_factory() as session:
            entity = await session.get(self.entity_class, key)
            return self.entity_to_domain(entity) if entity else None
    
    async def find_all(self, **filters) -> List[Domain]:
        """모든 엔티티 조회 (필터링 가능)"""
        async with self.session_factory() as session:
            stmt = select(self.entity_class)
            
            # 필터 조건 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        stmt = stmt.where(getattr(self.entity_class, key) == value)
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            return [self.entity_to_domain(entity) for entity in entities]
    
    async def find_with_pagination(
        self, 
        page: int = 1, 
        per_page: int = 10, 
        **filters
    ) -> List[Domain]:
        """페이지네이션을 적용한 조회"""
        offset = (page - 1) * per_page
        
        async with self.session_factory() as session:
            stmt = select(self.entity_class)
            
            # 필터 조건 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        stmt = stmt.where(getattr(self.entity_class, key) == value)
            
            stmt = stmt.offset(offset).limit(per_page)
            result = await session.execute(stmt)
            entities = result.scalars().all()
            return [self.entity_to_domain(entity) for entity in entities]
    
    async def find_all_sorted(
        self, 
        sort_by: str, 
        sort_order: str = "asc", 
        **filters
    ) -> List[Domain]:
        """정렬된 결과 조회"""
        async with self.session_factory() as session:
            stmt = select(self.entity_class)
            
            # 필터 조건 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        stmt = stmt.where(getattr(self.entity_class, key) == value)
            
            # 정렬 조건 적용
            if hasattr(self.entity_class, sort_by):
                sort_column = getattr(self.entity_class, sort_by)
                if sort_order.lower() == "desc":
                    stmt = stmt.order_by(desc(sort_column))
                else:
                    stmt = stmt.order_by(asc(sort_column))
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            return [self.entity_to_domain(entity) for entity in entities]
    
    async def update(self, domain: Domain) -> Optional[Domain]:
        """엔티티 업데이트"""
        key = self.get_primary_key(domain)
        
        async with self.session_factory() as session:
            entity = await session.get(self.entity_class, key)
            if not entity:
                return None
            
            self.update_entity_from_domain(entity, domain)
            await session.flush()
            await session.refresh(entity)
            return self.entity_to_domain(entity)
    
    async def update_fields(self, key: DomainKey, **fields) -> bool:
        """특정 필드들만 업데이트"""
        async with self.session_factory() as session:
            stmt = (
                update(self.entity_class)
                .where(self.entity_class.id == key)  # 기본 키가 id라고 가정
                .values(**fields)
            )
            result = await session.execute(stmt)
            return result.rowcount > 0
    
    async def delete(self, key: DomainKey) -> bool:
        """엔티티 삭제"""
        async with self.session_factory() as session:
            entity = await session.get(self.entity_class, key)
            if not entity:
                return False
            
            await session.delete(entity)
            return True
    
    async def delete_by_filter(self, **filters) -> int:
        """조건에 맞는 엔티티들 삭제"""
        async with self.session_factory() as session:
            stmt = delete(self.entity_class)
            
            # 필터 조건 적용
            for key, value in filters.items():
                if hasattr(self.entity_class, key):
                    stmt = stmt.where(getattr(self.entity_class, key) == value)
            
            result = await session.execute(stmt)
            return result.rowcount
    
    async def count(self, **filters) -> int:
        """엔티티 개수 조회"""
        async with self.session_factory() as session:
            stmt = select(func.count(self.entity_class.id))
            
            # 필터 조건 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        stmt = stmt.where(getattr(self.entity_class, key) == value)
            
            result = await session.execute(stmt)
            return result.scalar()
    
    async def exists(self, key: DomainKey) -> bool:
        """엔티티 존재 여부 확인"""
        async with self.session_factory() as session:
            stmt = select(func.count(self.entity_class.id)).where(
                self.entity_class.id == key
            )
            result = await session.execute(stmt)
            return result.scalar() > 0
    
    # ==================== 고급 쿼리 메서드들 ====================
    
    async def execute_raw_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """원시 SQL 쿼리 실행"""
        async with self.session_factory() as session:
            try:
                if params:
                    result = await session.execute(query, params)
                else:
                    result = await session.execute(query)
                
                # 결과를 딕셔너리 리스트로 변환
                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    data = [dict(zip(columns, row)) for row in rows]
                    row_count = len(data)
                else:
                    data = []
                    row_count = result.rowcount
                
                return QueryResult(
                    success=True,
                    data=data,
                    row_count=row_count,
                    query=query
                )
                
            except Exception as e:
                logger.error(f"Raw query 실행 오류: {e}")
                return QueryResult(
                    success=False,
                    data=[],
                    row_count=0,
                    error=str(e),
                    query=query
                )
