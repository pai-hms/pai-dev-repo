"""
Database Domain Models
비즈니스 로직과 데이터 검증을 담당하는 도메인 모델들
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class StatisticsData:
    """통계 데이터 도메인 모델"""
    region_code: str
    region_name: str 
    year: int
    population: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    source: str = "sgis"
    
    def validate(self) -> bool:
        """데이터 유효성 검증"""
        if not self.year or self.year < 2000:
            return False
        if not self.region_code or len(self.region_code) < 2:
            return False
        if not self.region_name:
            return False
        return True


@dataclass
class QueryResult:
    """쿼리 결과 도메인 모델"""
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    error: Optional[str] = None
    execution_time: Optional[float] = None
    query: Optional[str] = None
    
    def is_empty(self) -> bool:
        """결과가 비어있는지 확인"""
        return len(self.data) == 0
    
    def get_summary(self) -> Dict[str, Any]:
        """결과 요약 정보"""
        return {
            "success": self.success,
            "total_rows": len(self.data),
            "row_count": self.row_count,
            "execution_time": self.execution_time,
            "has_data": not self.is_empty(),
            "error": self.error
        }
