"""
검색 서비스
RAG 시스템의 Retrieval 단계를 담당하는 통합 서비스
"""
import logging
from typing import List, Dict, Any, Optional

from src.rag.embeddings.models import SearchResult
from src.rag.vector.search import VectorSearchService
from src.rag.embeddings.service import EmbeddingService
from .ranker import SearchRanker

logger = logging.getLogger(__name__)


class RetrievalService:
    """검색 서비스 (RAG Retrieval 단계 담당)"""
    
    def __init__(self, 
                 embedding_service: Optional[EmbeddingService] = None,
                 vector_search_service: Optional[VectorSearchService] = None,
                 ranker: Optional[SearchRanker] = None):
        """
        검색 서비스 초기화
        
        Args:
            embedding_service: 임베딩 서비스
            vector_search_service: 벡터 검색 서비스
            ranker: 검색 결과 순위 매기기 서비스
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_search_service = vector_search_service or VectorSearchService(self.embedding_service)
        self.ranker = ranker or SearchRanker()
    
    async def retrieve_relevant_documents(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        enable_ranking: bool = True,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        쿼리와 관련된 문서들을 검색하고 순위를 매겨서 반환
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 개수
            similarity_threshold: 유사도 임계값
            enable_ranking: 순위 매기기 활성화 여부
            metadata_filters: 메타데이터 필터 조건
            
        Returns:
            관련 문서 검색 결과 리스트
        """
        try:
            logger.info(f"문서 검색 시작: '{query}' (top_k={top_k})")
            
            # 벡터 검색 실행
            if metadata_filters:
                results = await self.vector_search_service.search_hybrid(
                    query=query,
                    metadata_filters=metadata_filters,
                    limit=top_k * 2,  # 여유분 확보
                    similarity_threshold=similarity_threshold
                )
            else:
                results = await self.vector_search_service.search_similar(
                    query=query,
                    limit=top_k * 2,
                    similarity_threshold=similarity_threshold
                )
            
            if not results:
                logger.warning(f"검색 결과 없음: '{query}'")
                return []
            
            logger.info(f"초기 검색 결과: {len(results)}개")
            
            # 순위 매기기 및 필터링
            if enable_ranking:
                # 임계값 필터링
                results = self.ranker.filter_by_threshold(results, similarity_threshold)
                
                # 중복 제거
                results = self.ranker.deduplicate_by_content(results)
                
                # 복합 순위 매기기
                results = self.ranker.rank_hybrid(results)
            
            # 최종 결과 제한
            final_results = results[:top_k]
            
            logger.info(f"문서 검색 완료: {len(final_results)}개 결과 반환")
            return final_results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    async def retrieve_by_categories(
        self,
        query: str,
        categories: List[str],
        top_k_per_category: int = 2
    ) -> Dict[str, List[SearchResult]]:
        """
        카테고리별로 문서 검색
        
        Args:
            query: 검색 쿼리
            categories: 검색할 카테고리(테이블) 리스트
            top_k_per_category: 카테고리별 반환할 결과 개수
            
        Returns:
            카테고리별 검색 결과 딕셔너리
        """
        try:
            logger.info(f"카테고리별 검색 시작: '{query}' in {categories}")
            
            results_by_category = {}
            
            for category in categories:
                try:
                    category_results = await self.vector_search_service.search_similar(
                        query=query,
                        limit=top_k_per_category,
                        source_tables=[category]
                    )
                    
                    # 순위 매기기
                    if category_results:
                        category_results = self.ranker.rank_by_similarity(category_results)
                    
                    results_by_category[category] = category_results
                    logger.debug(f"카테고리 '{category}': {len(category_results)}개 결과")
                    
                except Exception as e:
                    logger.error(f"카테고리 '{category}' 검색 실패: {e}")
                    results_by_category[category] = []
            
            total_results = sum(len(results) for results in results_by_category.values())
            logger.info(f"카테고리별 검색 완료: 총 {total_results}개 결과")
            
            return results_by_category
            
        except Exception as e:
            logger.error(f"카테고리별 검색 실패: {e}")
            return {}
    
    async def retrieve_context_for_sql(
        self,
        query: str,
        include_schema_info: bool = True
    ) -> str:
        """
        SQL 생성을 위한 컨텍스트 검색
        
        Args:
            query: 검색 쿼리
            include_schema_info: 스키마 정보 포함 여부
            
        Returns:
            SQL 생성에 도움이 되는 컨텍스트 문자열
        """
        try:
            logger.info(f"SQL 컨텍스트 검색: '{query}'")
            
            # 관련 문서 검색
            results = await self.retrieve_relevant_documents(
                query=query,
                top_k=3,
                similarity_threshold=0.2
            )
            
            if not results:
                return "관련된 통계 데이터를 찾을 수 없습니다."
            
            # 컨텍스트 구성
            context_parts = []
            
            context_parts.append("🔍 검색된 관련 데이터:")
            for i, result in enumerate(results, 1):
                context_parts.append(f"\n{i}. {result.content}")
                context_parts.append(f"   출처: {result.source_table}")
                context_parts.append(f"   유사도: {result.similarity:.3f}")
                
                # 메타데이터 정보 추가
                if result.metadata:
                    relevant_meta = []
                    for key, value in result.metadata.items():
                        if value and key in ['year', 'total_population', 'avg_age']:
                            relevant_meta.append(f"{key}: {value}")
                    if relevant_meta:
                        context_parts.append(f"   정보: {', '.join(relevant_meta)}")
            
            # 스키마 정보 추가
            if include_schema_info:
                context_parts.append("\n📊 사용 가능한 테이블 정보:")
                context_parts.append("- population_stats: 인구 통계 (tot_ppltn, avg_age, ppltn_dnsty 등)")
                context_parts.append("- household_stats: 가구 통계")
                context_parts.append("- company_stats: 사업체 통계")
            
            context = "\n".join(context_parts)
            logger.info(f"SQL 컨텍스트 생성 완료: {len(context)}자")
            
            return context
            
        except Exception as e:
            logger.error(f"SQL 컨텍스트 검색 실패: {e}")
            return f"컨텍스트 검색 중 오류 발생: {str(e)}"
    
    def format_search_results(self, results: List[SearchResult]) -> str:
        """
        검색 결과를 사용자 친화적인 문자열로 포맷팅
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            포맷팅된 검색 결과 문자열
        """
        if not results:
            return "검색 결과가 없습니다."
        
        lines = [f"🔍 검색 결과 ({len(results)}개):", ""]
        
        for i, result in enumerate(results, 1):
            lines.append(f"**{i}. {result.source_table}**")
            lines.append(f"   내용: {result.content}")
            lines.append(f"   유사도: {result.similarity:.3f}")
            
            if result.metadata:
                meta_info = []
                for key, value in result.metadata.items():
                    if value and key in ['year', 'total_population', 'avg_age']:
                        meta_info.append(f"{key}: {value}")
                if meta_info:
                    lines.append(f"   정보: {', '.join(meta_info)}")
            lines.append("")
        
        return "\n".join(lines)
