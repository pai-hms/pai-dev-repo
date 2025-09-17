"""
임베딩 생성 서비스
데이터 주권 원칙에 따라 임베딩 생성과 관련된 모든 제어권을 담당
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings

from .models import EmbeddingConfig, EmbeddingResult
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """임베딩 생성 서비스 (데이터 주권 원칙 적용)"""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        임베딩 서비스 초기화
        
        Args:
            config: 임베딩 설정 (None이면 기본 설정 사용)
        """
        self.config = config or EmbeddingConfig()
        if not self.config.validate():
            raise ValueError("Invalid embedding configuration")
        
        self.settings = get_settings()
        self._embeddings_client: Optional[OpenAIEmbeddings] = None
    
    @property
    def embeddings_client(self) -> OpenAIEmbeddings:
        """OpenAI 임베딩 클라이언트 (지연 로딩)"""
        if self._embeddings_client is None:
            self._embeddings_client = OpenAIEmbeddings(
                model=self.config.model_name,
                openai_api_key=self.settings.openai_api_key
            )
        return self._embeddings_client
    
    async def embed_single_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩으로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터
        """
        try:
            vector = await self.embeddings_client.aembed_query(text)
            return vector
        except Exception as e:
            logger.error(f"단일 텍스트 임베딩 실패: {e}")
            raise
    
    async def embed_batch_texts(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩 변환 (성능 최적화)
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            # 배치 크기에 따라 분할 처리
            vectors = []
            for i in range(0, len(texts), self.config.batch_size):
                batch = texts[i:i + self.config.batch_size]
                batch_vectors = await self.embeddings_client.aembed_documents(batch)
                vectors.extend(batch_vectors)
            
            return vectors
        except Exception as e:
            logger.error(f"배치 텍스트 임베딩 실패: {e}")
            raise
    
    def create_embedding_result(
        self, 
        content: str, 
        vector: List[float],
        source_table: str,
        source_id: str,
        metadata: Dict[str, Any]
    ) -> EmbeddingResult:
        """
        임베딩 결과 객체 생성
        
        Args:
            content: 원본 텍스트
            vector: 임베딩 벡터
            source_table: 출처 테이블
            source_id: 출처 ID
            metadata: 메타데이터
            
        Returns:
            임베딩 결과 객체
        """
        return EmbeddingResult(
            content=content,
            vector=vector,
            source_table=source_table,
            source_id=source_id,
            metadata=metadata
        )
    
    async def create_population_embeddings(self, year: int = 2023) -> List[EmbeddingResult]:
        """
        인구 통계 데이터 임베딩 생성
        
        Args:
            year: 대상 연도
            
        Returns:
            임베딩 결과 리스트
        """
        from src.database.connection import get_database_manager
        from src.database.repository import DatabaseService
        
        try:
            # 통계 데이터 조회
            summary_query = """
            SELECT 
                CONCAT('stats_', adm_cd, '_', year) as record_id,
                adm_cd,
                adm_nm,
                year,
                tot_ppltn,
                avg_age,
                ppltn_dnsty,
                male_ppltn,
                female_ppltn,
                CONCAT(
                    adm_nm, ' ', year, '년 통계: ',
                    '총인구 ', COALESCE(tot_ppltn::text, '정보없음'), '명, ',
                    '평균연령 ', COALESCE(avg_age::text, '정보없음'), '세, ',
                    '인구밀도 ', COALESCE(ppltn_dnsty::text, '정보없음'), '명/㎢, ',
                    '남성 ', COALESCE(male_ppltn::text, '정보없음'), '명, ',
                    '여성 ', COALESCE(female_ppltn::text, '정보없음'), '명'
                ) as description
            FROM population_stats 
            WHERE year = $1
            AND tot_ppltn IS NOT NULL
            ORDER BY adm_cd
            """
            
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                db_service = DatabaseService(session)
                
                # 수정: text() 함수 사용하여 SQL 텍스트를 명시적으로 선언
                from sqlalchemy import text
                
                result = await session.execute(
                    text(summary_query.replace('$1', str(year)))
                )
                rows = result.fetchall()
                columns = result.keys()
                stats = [dict(zip(columns, row)) for row in rows]
            
            if not stats:
                logger.warning(f"{year}년 통계 데이터를 찾을 수 없습니다.")
                return []
            
            # 설명문만 추출
            descriptions = [stat['description'] for stat in stats]
            
            # 배치 임베딩 생성
            vectors = await self.embed_batch_texts(descriptions)
            
            # 임베딩 결과 객체 생성
            embedding_results = []
            for stat, vector in zip(stats, vectors):
                metadata = {
                    'year': stat['year'],
                    'total_population': stat['tot_ppltn'],
                    'avg_age': stat['avg_age'],
                    'population_density': stat['ppltn_dnsty'],
                    'male_population': stat['male_ppltn'],
                    'female_population': stat['female_ppltn']
                }
                
                result = self.create_embedding_result(
                    content=stat['description'],
                    vector=vector,
                    source_table='population_stats',
                    source_id=stat['record_id'],
                    metadata=metadata
                )
                embedding_results.append(result)
            
            logger.info(f"{year}년 통계 데이터 {len(embedding_results)}개 임베딩 생성 완료")
            return embedding_results
            
        except Exception as e:
            logger.error(f"인구 통계 임베딩 생성 실패: {e}")
            raise
