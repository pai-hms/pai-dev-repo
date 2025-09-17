"""
검색 결과 순위 매기기 서비스
검색 결과의 관련성과 품질을 평가하여 순위를 조정
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.rag.embeddings.models import SearchResult

logger = logging.getLogger(__name__)


class SearchRanker:
    """검색 결과 순위 매기기 서비스"""
    
    def __init__(self):
        """순위 매기기 서비스 초기화"""
        pass
    
    def rank_by_similarity(self, results: List[SearchResult], reverse: bool = True) -> List[SearchResult]:
        """
        유사도 기준으로 검색 결과 순위 매기기
        
        Args:
            results: 검색 결과 리스트
            reverse: True면 내림차순, False면 오름차순
            
        Returns:
            순위가 매겨진 검색 결과 리스트
        """
        return sorted(results, key=lambda x: x.similarity, reverse=reverse)
    
    def rank_by_recency(self, results: List[SearchResult], reverse: bool = True) -> List[SearchResult]:
        """
        최신성 기준으로 검색 결과 순위 매기기
        
        Args:
            results: 검색 결과 리스트
            reverse: True면 최신순, False면 오래된순
            
        Returns:
            순위가 매겨진 검색 결과 리스트
        """
        def get_year(result: SearchResult) -> int:
            """메타데이터에서 연도 추출"""
            try:
                return int(result.metadata.get('year', 0))
            except (ValueError, TypeError):
                return 0
        
        return sorted(results, key=get_year, reverse=reverse)
    
    def rank_by_data_quality(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        데이터 품질 기준으로 검색 결과 순위 매기기
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            순위가 매겨진 검색 결과 리스트
        """
        def quality_score(result: SearchResult) -> float:
            """데이터 품질 점수 계산"""
            score = 0.0
            metadata = result.metadata
            
            # 데이터 완성도 평가
            if metadata.get('total_population'):
                score += 1.0
            if metadata.get('avg_age'):
                score += 1.0
            if metadata.get('population_density'):
                score += 1.0
            
            # 최신성 가점 (2020년 이후)
            year = metadata.get('year', 0)
            if isinstance(year, int) and year >= 2020:
                score += 0.5
            
            # 유사도 가중치
            score += result.similarity * 2.0
            
            return score
        
        return sorted(results, key=quality_score, reverse=True)
    
    def rank_hybrid(
        self, 
        results: List[SearchResult],
        similarity_weight: float = 0.6,
        recency_weight: float = 0.2,
        quality_weight: float = 0.2
    ) -> List[SearchResult]:
        """
        복합 기준으로 검색 결과 순위 매기기
        
        Args:
            results: 검색 결과 리스트
            similarity_weight: 유사도 가중치
            recency_weight: 최신성 가중치
            quality_weight: 품질 가중치
            
        Returns:
            순위가 매겨진 검색 결과 리스트
        """
        if not results:
            return results
        
        # 정규화를 위한 최대값 계산
        max_similarity = max(r.similarity for r in results) if results else 1.0
        max_year = max(int(r.metadata.get('year', 0)) for r in results) if results else 2023
        min_year = min(int(r.metadata.get('year', 0)) for r in results) if results else 2000
        year_range = max_year - min_year if max_year > min_year else 1
        
        def hybrid_score(result: SearchResult) -> float:
            """복합 점수 계산"""
            # 유사도 점수 (0-1)
            similarity_score = result.similarity / max_similarity if max_similarity > 0 else 0
            
            # 최신성 점수 (0-1)
            year = int(result.metadata.get('year', min_year))
            recency_score = (year - min_year) / year_range if year_range > 0 else 0
            
            # 품질 점수 (0-1)
            quality_score = 0.0
            metadata = result.metadata
            quality_factors = ['total_population', 'avg_age', 'population_density']
            available_factors = sum(1 for factor in quality_factors if metadata.get(factor))
            quality_score = available_factors / len(quality_factors)
            
            # 가중 합계
            total_score = (
                similarity_score * similarity_weight +
                recency_score * recency_weight +
                quality_score * quality_weight
            )
            
            return total_score
        
        ranked_results = sorted(results, key=hybrid_score, reverse=True)
        logger.debug(f"복합 순위 매기기 완료: {len(results)}개 결과")
        return ranked_results
    
    def filter_by_threshold(
        self, 
        results: List[SearchResult], 
        similarity_threshold: float = 0.5
    ) -> List[SearchResult]:
        """
        유사도 임계값으로 검색 결과 필터링
        
        Args:
            results: 검색 결과 리스트
            similarity_threshold: 유사도 임계값
            
        Returns:
            필터링된 검색 결과 리스트
        """
        filtered = [r for r in results if r.similarity >= similarity_threshold]
        logger.debug(f"임계값 필터링: {len(results)} -> {len(filtered)}개 결과")
        return filtered
    
    def deduplicate_by_content(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        내용 기준으로 중복 제거
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            중복이 제거된 검색 결과 리스트
        """
        seen_content = set()
        deduplicated = []
        
        for result in results:
            content_key = result.content.strip()[:100]  # 앞 100자로 비교
            if content_key not in seen_content:
                seen_content.add(content_key)
                deduplicated.append(result)
        
        logger.debug(f"내용 중복 제거: {len(results)} -> {len(deduplicated)}개 결과")
        return deduplicated
