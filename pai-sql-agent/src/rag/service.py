"""
RAG 통합 서비스 (Facade 패턴)
RAG 시스템의 모든 기능을 통합하여 제공하는 단일 진입점
설계 원칙: Container을 통한 의존 관계 명세, SLAP, 데이터 주권
"""
import logging
from typing import List, Dict, Any, Optional

from .embeddings.service import EmbeddingService
from .embeddings.models import EmbeddingConfig, EmbeddingResult, SearchResult
from .vector.store import VectorStore
from .vector.search import VectorSearchService
from .retrieval.service import RetrievalService
from .retrieval.ranker import SearchRanker

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG 통합 서비스 (Facade 패턴)
    모든 RAG 관련 기능의 단일 진입점 제공
    """
    
    def __init__(self, embedding_config: Optional[EmbeddingConfig] = None):
        """
        RAG 서비스 초기화 (Container 패턴)
        
        Args:
            embedding_config: 임베딩 설정
        """
        self.embedding_config = embedding_config or EmbeddingConfig()
        
        # 의존성 주입 (DI Container 원칙)
        self.embedding_service = EmbeddingService(self.embedding_config)
        self.vector_store = VectorStore()
        self.vector_search_service = VectorSearchService(self.embedding_service)
        self.search_ranker = SearchRanker()
        self.retrieval_service = RetrievalService(
            embedding_service=self.embedding_service,
            vector_search_service=self.vector_search_service,
            ranker=self.search_ranker
        )
    
    # === 임베딩 관련 기능 (SLAP: 임베딩 추상화 수준) ===
    
    async def create_embeddings_for_population_stats(self, year: int = 2023) -> Dict[str, Any]:
        """
        인구 통계 데이터 임베딩 생성 및 저장
        
        Args:
            year: 대상 연도
            
        Returns:
            생성 결과 통계
        """
        try:
            logger.info(f"인구 통계 임베딩 생성 시작: {year}년")
            
            # 임베딩 생성
            embeddings = await self.embedding_service.create_population_embeddings(year)
            
            if not embeddings:
                return {
                    "success": False,
                    "message": f"{year}년 통계 데이터를 찾을 수 없습니다.",
                    "created_count": 0,
                    "error_count": 0
                }
            
            # 벡터 저장소에 저장
            save_result = await self.vector_store.save_embeddings_batch(embeddings)
            
            result = {
                "success": save_result["success_count"] > 0,
                "message": f"{year}년 통계 데이터 {save_result['success_count']}개의 임베딩을 생성했습니다.",
                "created_count": save_result["success_count"],
                "error_count": save_result["error_count"]
            }
            
            if save_result["error_count"] > 0:
                result["message"] += f" ({save_result['error_count']}개 오류 발생)"
            
            logger.info(f"인구 통계 임베딩 생성 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"인구 통계 임베딩 생성 실패: {e}")
            return {
                "success": False,
                "message": f"임베딩 생성 중 오류가 발생했습니다: {str(e)}",
                "created_count": 0,
                "error_count": 1
            }
    
    async def get_embedding_statistics(self) -> Dict[str, Any]:
        """
        임베딩 저장소 통계 조회
        
        Returns:
            임베딩 통계 정보
        """
        try:
            stats = await self.vector_store.get_embedding_stats()
            logger.info("임베딩 통계 조회 완료")
            return stats
        except Exception as e:
            logger.error(f"임베딩 통계 조회 실패: {e}")
            return {"error": str(e)}
    
    # === 검색 관련 기능 (SLAP: 검색 추상화 수준) ===
    
    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 개수
            similarity_threshold: 유사도 임계값
            metadata_filters: 메타데이터 필터
            
        Returns:
            검색 결과 리스트
        """
        try:
            results = await self.retrieval_service.retrieve_relevant_documents(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                metadata_filters=metadata_filters
            )
            
            logger.info(f"문서 검색 완료: '{query}' -> {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    async def search_for_sql_context(self, query: str) -> str:
        """
        SQL 생성을 위한 컨텍스트 검색
        
        Args:
            query: 검색 쿼리
            
        Returns:
            SQL 생성에 도움이 되는 컨텍스트
        """
        try:
            context = await self.retrieval_service.retrieve_context_for_sql(query)
            logger.info(f"SQL 컨텍스트 검색 완료: '{query}'")
            return context
        except Exception as e:
            logger.error(f"SQL 컨텍스트 검색 실패: {e}")
            return f"컨텍스트 검색 중 오류 발생: {str(e)}"
    
    async def search_by_categories(
        self,
        query: str,
        categories: List[str],
        top_k_per_category: int = 2
    ) -> Dict[str, List[SearchResult]]:
        """
        카테고리별 문서 검색
        
        Args:
            query: 검색 쿼리
            categories: 검색할 카테고리 리스트
            top_k_per_category: 카테고리별 결과 개수
            
        Returns:
            카테고리별 검색 결과
        """
        try:
            results = await self.retrieval_service.retrieve_by_categories(
                query=query,
                categories=categories,
                top_k_per_category=top_k_per_category
            )
            
            total_results = sum(len(r) for r in results.values())
            logger.info(f"카테고리별 검색 완료: '{query}' -> {total_results}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"카테고리별 검색 실패: {e}")
            return {}
    
    # === 관리 기능 (SLAP: 관리 추상화 수준) ===
    
    async def clear_embeddings_by_source(self, source_table: str) -> Dict[str, Any]:
        """
        특정 소스의 임베딩 삭제
        
        Args:
            source_table: 삭제할 소스 테이블명
            
        Returns:
            삭제 결과
        """
        try:
            deleted_count = await self.vector_store.delete_embeddings_by_source(source_table)
            
            result = {
                "success": True,
                "message": f"{source_table}에서 {deleted_count}개 임베딩을 삭제했습니다.",
                "deleted_count": deleted_count
            }
            
            logger.info(f"임베딩 삭제 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"임베딩 삭제 실패: {e}")
            return {
                "success": False,
                "message": f"임베딩 삭제 중 오류가 발생했습니다: {str(e)}",
                "deleted_count": 0
            }
    
    async def rebuild_embeddings(self, year: int = 2023, clear_existing: bool = True) -> Dict[str, Any]:
        """
        임베딩 재구축 (기존 데이터 삭제 후 새로 생성)
        
        Args:
            year: 대상 연도
            clear_existing: 기존 데이터 삭제 여부
            
        Returns:
            재구축 결과
        """
        try:
            logger.info(f"임베딩 재구축 시작: {year}년 (clear_existing={clear_existing})")
            
            results = {"steps": []}
            
            # 기존 데이터 삭제
            if clear_existing:
                clear_result = await self.clear_embeddings_by_source("population_stats")
                results["steps"].append({
                    "step": "clear_existing",
                    "success": clear_result["success"],
                    "deleted_count": clear_result["deleted_count"]
                })
            
            # 새 임베딩 생성
            create_result = await self.create_embeddings_for_population_stats(year)
            results["steps"].append({
                "step": "create_embeddings",
                "success": create_result["success"],
                "created_count": create_result["created_count"],
                "error_count": create_result["error_count"]
            })
            
            # 전체 결과
            results["success"] = create_result["success"]
            results["message"] = f"임베딩 재구축 완료: {create_result['created_count']}개 생성"
            
            if create_result["error_count"] > 0:
                results["message"] += f" ({create_result['error_count']}개 오류)"
            
            logger.info(f"임베딩 재구축 완료: {results}")
            return results
            
        except Exception as e:
            logger.error(f"임베딩 재구축 실패: {e}")
            return {
                "success": False,
                "message": f"임베딩 재구축 중 오류가 발생했습니다: {str(e)}",
                "steps": []
            }
    
    # === 유틸리티 기능 ===
    
    def format_search_results_for_display(self, results: List[SearchResult]) -> str:
        """
        검색 결과를 표시용으로 포맷팅
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            포맷팅된 결과 문자열
        """
        return self.retrieval_service.format_search_results(results)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        RAG 시스템 상태 확인
        
        Returns:
            시스템 상태 정보
        """
        try:
            # 임베딩 통계 확인
            stats = await self.get_embedding_statistics()
            
            # 간단한 검색 테스트
            test_results = await self.search_similar_documents("인구", top_k=1)
            
            health_info = {
                "status": "healthy",
                "embedding_stats": stats,
                "search_test": {
                    "success": len(test_results) > 0,
                    "result_count": len(test_results)
                },
                "services": {
                    "embedding_service": "available",
                    "vector_store": "available", 
                    "vector_search": "available",
                    "retrieval_service": "available"
                }
            }
            
            logger.info("RAG 시스템 상태 확인 완료")
            return health_info
            
        except Exception as e:
            logger.error(f"RAG 시스템 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "services": {
                    "embedding_service": "unknown",
                    "vector_store": "unknown",
                    "vector_search": "unknown", 
                    "retrieval_service": "unknown"
                }
            }


# === 전역 RAG 서비스 인스턴스 (Singleton 패턴) ===

_rag_service_instance: Optional[RAGService] = None


def get_rag_service(embedding_config: Optional[EmbeddingConfig] = None) -> RAGService:
    """
    전역 RAG 서비스 인스턴스 반환 (Singleton)
    
    Args:
        embedding_config: 임베딩 설정 (첫 생성 시에만 적용)
        
    Returns:
        RAG 서비스 인스턴스
    """
    global _rag_service_instance
    
    if _rag_service_instance is None:
        _rag_service_instance = RAGService(embedding_config)
        logger.info("전역 RAG 서비스 인스턴스 생성 완료")
    
    return _rag_service_instance


def reset_rag_service() -> None:
    """전역 RAG 서비스 인스턴스 리셋 (테스트용)"""
    global _rag_service_instance
    _rag_service_instance = None
    logger.info("전역 RAG 서비스 인스턴스 리셋 완료")
