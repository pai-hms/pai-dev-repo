"""
벡터 검색 서비스
데이터 주권 원칙에 따라 벡터 유사도 검색을 담당
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text

from src.rag.embeddings.models import SearchResult
from src.rag.embeddings.service import EmbeddingService
from src.database.connection import get_database_manager

logger = logging.getLogger(__name__)


class VectorSearchService:
    """벡터 검색 서비스 (데이터 주권 원칙 적용)"""
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        벡터 검색 서비스 초기화
        
        Args:
            embedding_service: 임베딩 서비스 (None이면 새로 생성)
        """
        self.embedding_service = embedding_service or EmbeddingService()
    
    async def search_similar(
        self, 
        query: str, 
        limit: int = 5,
        similarity_threshold: float = 0.0,
        source_tables: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            limit: 반환할 결과 개수
            similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)
            source_tables: 검색할 소스 테이블 리스트 (None이면 전체)
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리를 임베딩으로 변환
            query_vector = await self.embedding_service.embed_single_text(query)
            vector_str = f"[{','.join(map(str, query_vector))}]"
            
            # 검색 쿼리 구성
            base_query = """
            SELECT 
                content,
                source_table,
                source_id,
                meta_data,
                1 - (embedding <=> $1::vector) as similarity
            FROM document_embeddings
            WHERE embedding IS NOT NULL
            """
            
            params = {"query_vector": vector_str}
            
            # 소스 테이블 필터링
            if source_tables:
                base_query += " AND source_table = ANY($2::text[])"
                params["source_tables"] = source_tables
            
            # 유사도 임계값 적용
            if similarity_threshold > 0:
                threshold_param = "$3" if source_tables else "$2"
                base_query += f" AND (1 - (embedding <=> $1::vector)) >= {threshold_param}"
                params["threshold"] = similarity_threshold
            
            # 정렬 및 제한
            base_query += " ORDER BY embedding <=> $1::vector LIMIT $" + str(len(params) + 1)
            params["limit"] = limit
            
            # 검색 실행
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(text(base_query), params)
                rows = result.fetchall()
                
                # 검색 결과 변환
                search_results = []
                for row in rows:
                    search_result = SearchResult(
                        content=row.content,
                        source_table=row.source_table,
                        source_id=row.source_id,
                        metadata=row.meta_data or {},
                        similarity=float(row.similarity)
                    )
                    search_results.append(search_result)
                
                logger.info(f"벡터 검색 완료: '{query}' -> {len(search_results)}개 결과")
                return search_results
                
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []
    
    async def search_by_metadata(
        self, 
        metadata_filters: Dict[str, Any],
        limit: int = 10
    ) -> List[SearchResult]:
        """
        메타데이터 조건으로 문서 검색
        
        Args:
            metadata_filters: 메타데이터 필터 조건
            limit: 반환할 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 메타데이터 조건을 JSON 쿼리로 변환
            conditions = []
            params = {"limit": limit}
            
            for key, value in metadata_filters.items():
                param_name = f"meta_{key}"
                conditions.append(f"meta_data->>'{key}' = ${len(params) + 1}")
                params[param_name] = str(value)
            
            if not conditions:
                logger.warning("메타데이터 필터 조건이 비어있습니다")
                return []
            
            search_query = f"""
            SELECT 
                content,
                source_table,
                source_id,
                meta_data,
                0.0 as similarity
            FROM document_embeddings
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT $1
            """
            
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(text(search_query), params)
                rows = result.fetchall()
                
                search_results = []
                for row in rows:
                    search_result = SearchResult(
                        content=row.content,
                        source_table=row.source_table,
                        source_id=row.source_id,
                        metadata=row.meta_data or {},
                        similarity=0.0  # 메타데이터 검색에서는 유사도 없음
                    )
                    search_results.append(search_result)
                
                logger.info(f"메타데이터 검색 완료: {metadata_filters} -> {len(search_results)}개 결과")
                return search_results
                
        except Exception as e:
            logger.error(f"메타데이터 검색 실패: {e}")
            return []
    
    async def search_hybrid(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        벡터 유사도와 메타데이터를 결합한 하이브리드 검색
        
        Args:
            query: 검색 쿼리
            metadata_filters: 메타데이터 필터 조건
            limit: 반환할 결과 개수
            similarity_threshold: 유사도 임계값
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리를 임베딩으로 변환
            query_vector = await self.embedding_service.embed_single_text(query)
            vector_str = f"[{','.join(map(str, query_vector))}]"
            
            # 기본 검색 쿼리
            base_query = """
            SELECT 
                content,
                source_table,
                source_id,
                meta_data,
                1 - (embedding <=> $1::vector) as similarity
            FROM document_embeddings
            WHERE embedding IS NOT NULL
            """
            
            params = {"query_vector": vector_str}
            
            # 메타데이터 필터 추가
            if metadata_filters:
                for key, value in metadata_filters.items():
                    param_name = f"meta_{key}"
                    base_query += f" AND meta_data->>'{key}' = ${len(params) + 1}"
                    params[param_name] = str(value)
            
            # 유사도 임계값 적용
            if similarity_threshold > 0:
                base_query += f" AND (1 - (embedding <=> $1::vector)) >= ${len(params) + 1}"
                params["threshold"] = similarity_threshold
            
            # 정렬 및 제한
            base_query += f" ORDER BY embedding <=> $1::vector LIMIT ${len(params) + 1}"
            params["limit"] = limit
            
            # 검색 실행
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(text(base_query), params)
                rows = result.fetchall()
                
                search_results = []
                for row in rows:
                    search_result = SearchResult(
                        content=row.content,
                        source_table=row.source_table,
                        source_id=row.source_id,
                        metadata=row.meta_data or {},
                        similarity=float(row.similarity)
                    )
                    search_results.append(search_result)
                
                logger.info(f"하이브리드 검색 완료: '{query}' + {metadata_filters} -> {len(search_results)}개 결과")
                return search_results
                
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            return []
