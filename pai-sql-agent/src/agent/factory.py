"""
Agent Service Factory - DI Container 순환 참조 해결용
"""
import asyncio
import logging
from typing import Optional

from .service import SQLAgentService
from .graph import create_sql_agent_graph

logger = logging.getLogger(__name__)

# 전역 서비스 인스턴스 캐시
_agent_service: Optional[SQLAgentService] = None
_service_lock = asyncio.Lock()


async def get_agent_service() -> SQLAgentService:
    """
    Agent 서비스 인스턴스 반환 - DI 컨테이너 없이 직접 생성
    순환 import를 방지하기 위해 container를 거치지 않음
    """
    global _agent_service
    
    if _agent_service is None:
        async with _service_lock:
            if _agent_service is None:
                logger.info("Agent 서비스 직접 생성 시작")
                
                # Container 없이 직접 워크플로우 생성
                workflow = await create_sql_agent_graph()
                _agent_service = SQLAgentService(workflow)
                
                logger.info("Agent 서비스 직접 생성 완료")
    
    return _agent_service


def reset_agent_service():
    """Agent 서비스 인스턴스 리셋 (테스트용)"""
    global _agent_service
    _agent_service = None
