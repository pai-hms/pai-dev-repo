"""
LLM 컨테이너 (Legacy) - 기존 LLM 서비스 래핑
하위 호환성을 위해 유지되지만 새 프로젝트는 src.llm.service 직접 사용
"""
import logging
from .service import get_llm_service, LLMConfig

logger = logging.getLogger(__name__)


class LLMContainer:
    """
    Legacy LLM 컨테이너 - 하위 호환성용
    새 프로젝트는 src.llm.service.get_llm_service() 직접 사용
    """
    
    def __init__(self):
        logger.warning("LLMContainer는 deprecated입니다. src.llm.service 직접 사용하세요.")
    
    async def get_service(self):
        """LLM 서비스 인스턴스 (하위 호환성)"""
        return await get_llm_service()


# 하위 호환성을 위한 헬퍼 함수
async def create_llm_container():
    """LLM 컨테이너 생성 (하위 호환성)"""
    return LLMContainer()
