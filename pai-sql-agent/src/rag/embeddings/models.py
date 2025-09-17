"""
임베딩 관련 데이터 모델
데이터와 로직의 일체화 원칙에 따라 임베딩 데이터 구조와 관련 로직을 정의
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EmbeddingConfig:
    """임베딩 설정"""
    model_name: str = "text-embedding-3-small"
    dimension: int = 1536
    batch_size: int = 100
    max_tokens: int = 8192
    
    def validate(self) -> bool:
        """설정 유효성 검증"""
        return (
            self.dimension > 0 
            and self.batch_size > 0 
            and self.max_tokens > 0
            and self.model_name.strip() != ""
        )


@dataclass 
class EmbeddingResult:
    """임베딩 결과"""
    content: str
    vector: List[float]
    source_table: str
    source_id: str
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "content": self.content,
            "vector": self.vector,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    def vector_as_string(self) -> str:
        """벡터를 PostgreSQL vector 타입 문자열로 변환"""
        return f"[{','.join(map(str, self.vector))}]"


@dataclass
class SearchResult:
    """검색 결과"""
    content: str
    source_table: str
    source_id: str
    metadata: Dict[str, Any]
    similarity: float
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "content": self.content,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "metadata": self.metadata,
            "similarity": self.similarity
        }
