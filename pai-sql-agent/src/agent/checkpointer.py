"""
PostgreSQL 기반 Checkpointer
LangGraph의 상태를 PostgreSQL에 영속적으로 저장
"""
import json
import logging
from typing import Dict, Any, Optional, Iterator, Tuple
from datetime import datetime
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from sqlalchemy import Column, String, Text, DateTime, Integer, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database_manager
from src.database.models import Base as BaseModel


logger = logging.getLogger(__name__)


# Checkpointer용 별도 Base 사용 (순환 참조 방지)
CheckpointBase = declarative_base()


class CheckpointRecord(CheckpointBase):
    """체크포인트 레코드"""
    __tablename__ = "langgraph_checkpoints"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    thread_id = Column(String(255), nullable=False, comment="스레드 ID")
    checkpoint_id = Column(String(255), nullable=False, comment="체크포인트 ID")
    parent_checkpoint_id = Column(String(255), nullable=True, comment="부모 체크포인트 ID")
    
    # 체크포인트 데이터
    checkpoint_data = Column(Text, nullable=False, comment="체크포인트 데이터 (JSON)")
    meta_data = Column(Text, nullable=True, comment="메타데이터 (JSON)")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_checkpoint_thread_id", "thread_id"),
        Index("idx_checkpoint_checkpoint_id", "checkpoint_id"),
        Index("idx_checkpoint_parent_id", "parent_checkpoint_id"),
        Index("idx_checkpoint_created_at", "created_at"),
    )


class PostgresCheckpointSaver(BaseCheckpointSaver):
    """PostgreSQL 기반 체크포인트 저장기"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    async def _ensure_tables(self) -> None:
        """테이블 생성 확인"""
        try:
            async with self.db_manager.async_engine.begin() as conn:
                await conn.run_sync(CheckpointBase.metadata.create_all)
        except Exception as e:
            logger.error(f"체크포인트 테이블 생성 실패: {str(e)}")
            raise
    
    async def aget(
        self, 
        config: Dict[str, Any]
    ) -> Optional[Tuple[Checkpoint, CheckpointMetadata]]:
        """체크포인트 조회 (비동기)"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                return None
            
            await self._ensure_tables()
            
            async with self.db_manager.get_async_session() as session:
                # 최신 체크포인트 조회
                query = text("""
                    SELECT checkpoint_data, meta_data 
                    FROM langgraph_checkpoints 
                    WHERE thread_id = :thread_id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                
                result = await session.execute(
                    query, {"thread_id": thread_id}
                )
                row = result.fetchone()
                
                if not row:
                    return None
                
                # JSON 파싱
                checkpoint_data = json.loads(row[0])
                metadata_raw = row[1]
                meta_data = json.loads(metadata_raw) if metadata_raw else {}
                
                # Checkpoint 객체 생성
                checkpoint = Checkpoint(
                    v=checkpoint_data.get("v", 1),
                    id=checkpoint_data.get("id"),
                    ts=checkpoint_data.get("ts"),
                    channel_values=checkpoint_data.get("channel_values", {}),
                    channel_versions=checkpoint_data.get("channel_versions", {}),
                    versions_seen=checkpoint_data.get("versions_seen", {})
                )
                
                metadata = CheckpointMetadata(
                    source=meta_data.get("source", "input"),
                    step=meta_data.get("step", -1),
                    writes=meta_data.get("writes", {}),
                    parents=meta_data.get("parents", {})
                )
                
                return (checkpoint, metadata)
                
        except Exception as e:
            logger.error(f"체크포인트 조회 중 오류: {str(e)}")
            return None
    
    def get(
        self, 
        config: Dict[str, Any]
    ) -> Optional[Tuple[Checkpoint, CheckpointMetadata]]:
        """체크포인트 조회 (동기)"""
        # 비동기 메서드를 동기로 래핑
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.aget(config))
        except RuntimeError:
            # 새 이벤트 루프 생성
            return asyncio.run(self.aget(config))
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata
    ) -> None:
        """체크포인트 저장 (비동기)"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                raise ValueError("thread_id가 필요합니다")
            
            await self._ensure_tables()
            
            # 체크포인트 데이터 직렬화
            checkpoint_data = {
                "v": checkpoint.v,
                "id": checkpoint.id,
                "ts": checkpoint.ts,
                "channel_values": checkpoint.channel_values,
                "channel_versions": checkpoint.channel_versions,
                "versions_seen": checkpoint.versions_seen
            }
            
            meta_data = {
                "source": metadata.source,
                "step": metadata.step,
                "writes": metadata.writes,
                "parents": metadata.parents
            }
            
            async with self.db_manager.get_async_session() as session:
                # 기존 체크포인트 확인
                query = text("""
                    SELECT id FROM langgraph_checkpoints 
                    WHERE thread_id = :thread_id AND checkpoint_id = :checkpoint_id
                """)
                
                result = await session.execute(
                    query, {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint.id
                    }
                )
                existing = result.fetchone()
                
                if existing:
                    # 업데이트
                    update_query = text("""
                        UPDATE langgraph_checkpoints 
                        SET checkpoint_data = :checkpoint_data,
                            meta_data = :meta_data,
                            updated_at = :updated_at
                        WHERE thread_id = :thread_id AND checkpoint_id = :checkpoint_id
                    """)
                    
                    await session.execute(
                        update_query, {
                            "thread_id": thread_id,
                            "checkpoint_id": checkpoint.id,
                            "checkpoint_data": json.dumps(checkpoint_data),
                            "meta_data": json.dumps(meta_data),
                            "updated_at": datetime.utcnow()
                        }
                    )
                else:
                    # 삽입
                    insert_query = text("""
                        INSERT INTO langgraph_checkpoints 
                        (id, thread_id, checkpoint_id, checkpoint_data, meta_data, created_at, updated_at)
                        VALUES (:id, :thread_id, :checkpoint_id, :checkpoint_data, :meta_data, :created_at, :updated_at)
                    """)
                    
                    await session.execute(
                        insert_query, {
                            "id": str(uuid4()),
                            "thread_id": thread_id,
                            "checkpoint_id": checkpoint.id,
                            "checkpoint_data": json.dumps(checkpoint_data),
                            "meta_data": json.dumps(meta_data),
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"체크포인트 저장 중 오류: {str(e)}")
            raise
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata
    ) -> None:
        """체크포인트 저장 (동기)"""
        # 비동기 메서드를 동기로 래핑
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.aput(config, checkpoint, metadata))
        except RuntimeError:
            # 새 이벤트 루프 생성
            asyncio.run(self.aput(config, checkpoint, metadata))
    
    async def alist(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = None,
        before: Optional[str] = None
    ) -> Iterator[Tuple[Checkpoint, CheckpointMetadata]]:
        """체크포인트 목록 조회 (비동기)"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                return iter([])
            
            await self._ensure_tables()
            
            async with self.db_manager.get_async_session() as session:
                # 쿼리 구성
                base_query = """
                    SELECT checkpoint_data, meta_data 
                    FROM langgraph_checkpoints 
                    WHERE thread_id = :thread_id
                """
                params = {"thread_id": thread_id}
                
                if before:
                    base_query += " AND created_at < :before"
                    params["before"] = before
                
                base_query += " ORDER BY created_at DESC"
                
                if limit:
                    base_query += " LIMIT :limit"
                    params["limit"] = limit
                
                result = await session.execute(text(base_query), params)
                rows = result.fetchall()
                
                checkpoints = []
                for row in rows:
                    checkpoint_data = json.loads(row[0])
                    metadata_raw = row[1]
                    meta_data = json.loads(metadata_raw) if metadata_raw else {}
                    
                    checkpoint = Checkpoint(
                        v=checkpoint_data.get("v", 1),
                        id=checkpoint_data.get("id"),
                        ts=checkpoint_data.get("ts"),
                        channel_values=checkpoint_data.get("channel_values", {}),
                        channel_versions=checkpoint_data.get("channel_versions", {}),
                        versions_seen=checkpoint_data.get("versions_seen", {})
                    )
                    
                    metadata = CheckpointMetadata(
                        source=meta_data.get("source", "input"),
                        step=meta_data.get("step", -1),
                        writes=meta_data.get("writes", {}),
                        parents=meta_data.get("parents", {})
                    )
                    
                    checkpoints.append((checkpoint, metadata))
                
                return iter(checkpoints)
                
        except Exception as e:
            logger.error(f"체크포인트 목록 조회 중 오류: {str(e)}")
            return iter([])
    
    def list(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = None,
        before: Optional[str] = None
    ) -> Iterator[Tuple[Checkpoint, CheckpointMetadata]]:
        """체크포인트 목록 조회 (동기)"""
        # 비동기 메서드를 동기로 래핑
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.alist(config, limit, before))
        except RuntimeError:
            # 새 이벤트 루프 생성
            return asyncio.run(self.alist(config, limit, before))


# 전역 체크포인터 인스턴스
_postgres_checkpointer: Optional[PostgresCheckpointSaver] = None


async def get_postgres_checkpointer() -> PostgresCheckpointSaver:
    """PostgreSQL 체크포인터 인스턴스 반환"""
    global _postgres_checkpointer
    if _postgres_checkpointer is None:
        _postgres_checkpointer = PostgresCheckpointSaver()
        await _postgres_checkpointer._ensure_tables()
    return _postgres_checkpointer