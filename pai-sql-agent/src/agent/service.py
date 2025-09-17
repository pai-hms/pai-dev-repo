"""
SQL Agent 서비스
싱글톤 패턴으로 단일 진입점 제공
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .graph import create_sql_agent_graph
from .nodes import create_initial_state
from .container import get_container

logger = logging.getLogger(__name__)


class SQLAgentService:
    """SQL Agent 서비스 - 싱글톤"""
    
    _instance: Optional['SQLAgentService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        if SQLAgentService._instance is not None:
            raise RuntimeError("SQLAgentService는 싱글톤입니다. get_instance()를 사용하세요.")
        
        self._agent_graph = None
        self._container = None
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'SQLAgentService':
        """싱글톤 인스턴스 가져오기"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """서비스 초기화"""
        if self._initialized:
            return
            
        logger.info("🚀 SQL Agent 서비스 초기화 시작")
        
        # 1. DI 컨테이너 초기화
        self._container = await get_container()
        
        # 2. 그래프 생성
        self._agent_graph = await create_sql_agent_graph()
        
        self._initialized = True
        logger.info("✅ SQL Agent 서비스 초기화 완료")
    
    async def query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        SQL 쿼리 실행
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID (선택사항)
        
        Returns:
            표준화된 응답 형식
        """
        start_time = datetime.now()
        session_id = session_id or f"session_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"🔍 SQL Agent 쿼리 시작: {question[:50]}...")
            
            # 초기 상태 생성
            initial_state = create_initial_state(question, session_id)
            
            # 그래프 실행
            result = await self._agent_graph.ainvoke(initial_state)
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 응답 포맷팅
            return self._format_response(result, processing_time)
            
        except Exception as e:
            logger.error(f"❌ SQL Agent 쿼리 실패: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": False,
                "message": f"쿼리 처리 중 오류가 발생했습니다: {str(e)}",
                "sql_queries": [],
                "results": [],
                "used_tools": [],
                "session_id": session_id,
                "processing_time": processing_time,
                "error_message": str(e)
            }
    
    def _format_response(self, agent_result: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """에이전트 결과를 표준 API 응답으로 변환"""
        success = agent_result.get("is_complete", False) and not agent_result.get("error_message")
        
        # SQL 쿼리 목록
        sql_queries = []
        if agent_result.get("generated_sql"):
            sql_queries.append(agent_result["generated_sql"])
        
        # 실행 결과 목록
        results = []
        if agent_result.get("execution_result"):
            results.append(agent_result["execution_result"])
        
        # 도구 사용 정보 표준화
        used_tools = []
        for tool in agent_result.get("used_tools", []):
            used_tools.append({
                "tool_name": tool.get("tool_name", "unknown"),
                "tool_function": tool.get("tool_name", "unknown"),  # 호환성
                "tool_description": "SQL 쿼리 실행",  # 호환성
                "arguments": {"query": agent_result.get("generated_sql", "")},  # 호환성
                "execution_order": 1,  # 호환성
                "success": tool.get("success", False),
                "result_preview": tool.get("result_preview", ""),
                "error_message": None
            })
        
        return {
            "success": success,
            "message": agent_result.get("final_response", "처리 완료"),
            "sql_queries": sql_queries,
            "results": results,
            "used_tools": used_tools,
            "session_id": agent_result.get("session_id", "unknown"),
            "processing_time": processing_time,
            "error_message": agent_result.get("error_message")
        }


# ===== 전역 접근 함수 =====

async def get_sql_agent_service() -> SQLAgentService:
    """SQL Agent 서비스 인스턴스 가져오기"""
    return await SQLAgentService.get_instance()


# ===== 호환성 함수 (기존 코드와의 호환성) =====

def get_sql_agent_service_sync(enable_checkpointer: bool = True) -> 'SQLAgentServiceWrapper':
    """기존 동기 방식 호환성을 위한 래퍼"""
    return SQLAgentServiceWrapper()


class SQLAgentServiceWrapper:
    """기존 인터페이스 호환성을 위한 래퍼 클래스"""
    
    async def invoke_query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """기존 invoke_query 메서드 호환성"""
        service = await get_sql_agent_service()
        return await service.query(question, session_id)