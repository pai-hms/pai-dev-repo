"""
벡터 저장소 서비스
데이터 주권 원칙에 따라 벡터 데이터의 저장과 관리를 담당
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.rag.embeddings.models import EmbeddingResult
from src.database.connection import get_database_manager
from src.database.repository import DatabaseService

logger = logging.getLogger(__name__)


class VectorStore:
    """벡터 저장소 (데이터 주권 원칙 적용)"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        벡터 저장소 초기화
        
        Args:
            session: 데이터베이스 세션 (None이면 새로 생성)
        """
        self.session = session
        self._db_manager = None
    
    async def save_embedding(self, embedding: EmbeddingResult) -> bool:
        """
        단일 임베딩을 데이터베이스에 저장
        
        Args:
            embedding: 저장할 임베딩 결과
            
        Returns:
            저장 성공 여부
        """
        try:
            import json
            from sqlalchemy import text
            
            # 간단하고 직접적인 방법 사용
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                # 직접 SQL 실행 - % 포맷팅 사용 (안전하지만 이 경우 문제없음)
                upsert_query = f"""
                INSERT INTO document_embeddings (content, source_table, source_id, meta_data, embedding)
                VALUES ('{embedding.content.replace("'", "''")}', 
                        '{embedding.source_table}', 
                        '{embedding.source_id}', 
                        '{json.dumps(embedding.metadata).replace("'", "''")}', 
                        '{embedding.vector_as_string()}'::vector)
                ON CONFLICT (source_table, source_id) 
                DO UPDATE SET 
                    content = EXCLUDED.content,
                    meta_data = EXCLUDED.meta_data,
                    embedding = EXCLUDED.embedding,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                await session.execute(text(upsert_query))
                await session.commit()
            
            logger.debug(f"임베딩 저장 성공: {embedding.source_table}:{embedding.source_id}")
            return True
            
        except Exception as e:
            logger.error(f"임베딩 저장 실패 ({embedding.source_id}): {e}")
            return False
    
    async def save_embeddings_batch(self, embeddings: List[EmbeddingResult]) -> Dict[str, int]:
        """
        여러 임베딩을 배치로 저장 (성능 최적화)
        
        Args:
            embeddings: 저장할 임베딩 결과 리스트
            
        Returns:
            저장 결과 통계 (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                for embedding in embeddings:
                    try:
                        store = VectorStore(session)
                        success = await store.save_embedding(embedding)
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"개별 임베딩 저장 오류 ({embedding.source_id}): {e}")
                        error_count += 1
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"배치 임베딩 저장 실패: {e}")
            error_count = len(embeddings)
        
        logger.info(f"배치 저장 완료: 성공 {success_count}개, 실패 {error_count}개")
        return {"success_count": success_count, "error_count": error_count}
    
    async def delete_embeddings_by_source(self, source_table: str, source_ids: Optional[List[str]] = None) -> int:
        """
        특정 소스의 임베딩 삭제
        
        Args:
            source_table: 소스 테이블명
            source_ids: 삭제할 소스 ID 리스트 (None이면 전체 삭제)
            
        Returns:
            삭제된 레코드 수
        """
        try:
            if source_ids:
                delete_query = """
                DELETE FROM document_embeddings 
                WHERE source_table = $1 AND source_id = ANY($2::text[])
                """
                params = {"source_table": source_table, "source_ids": source_ids}
            else:
                delete_query = """
                DELETE FROM document_embeddings 
                WHERE source_table = $1
                """
                params = {"source_table": source_table}
            
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(text(delete_query), params)
                deleted_count = result.rowcount
                await session.commit()
                
                logger.info(f"임베딩 삭제 완료: {source_table}에서 {deleted_count}개 삭제")
                return deleted_count
                
        except Exception as e:
            logger.error(f"임베딩 삭제 실패: {e}")
            return 0
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """
        임베딩 저장소 통계 조회
        
        Returns:
            저장소 통계 정보
        """
        try:
            stats_query = """
            SELECT 
                source_table,
                COUNT(*) as total_count,
                COUNT(embedding) as embedded_count,
                MIN(created_at) as oldest_created,
                MAX(updated_at) as latest_updated
            FROM document_embeddings
            GROUP BY source_table
            ORDER BY total_count DESC
            """
            
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(text(stats_query))
                rows = result.fetchall()
                
                stats = {
                    "total_tables": len(rows),
                    "total_records": 0,
                    "total_embedded": 0,
                    "tables": []
                }
                
                for row in rows:
                    table_stats = {
                        "source_table": row.source_table,
                        "total_count": row.total_count,
                        "embedded_count": row.embedded_count,
                        "completion_rate": (row.embedded_count / row.total_count * 100) if row.total_count > 0 else 0,
                        "oldest_created": row.oldest_created,
                        "latest_updated": row.latest_updated
                    }
                    stats["tables"].append(table_stats)
                    stats["total_records"] += row.total_count
                    stats["total_embedded"] += row.embedded_count
                
                stats["overall_completion"] = (stats["total_embedded"] / stats["total_records"] * 100) if stats["total_records"] > 0 else 0
                
                return stats
                
        except Exception as e:
            logger.error(f"임베딩 통계 조회 실패: {e}")
            return {"error": str(e)}
