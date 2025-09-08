# rag-server/src/llm/custom_llm.py
import httpx
import logging
from typing import Optional
from .domains import CompletionVendor, LLMCompletionModel
from .settings import LLMSettings

logger = logging.getLogger(__name__)

class CustomLLMService:
    """Custom LLM 관리 서비스 """
    
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        self._client = httpx.AsyncClient()
    
    async def check_health(self, model_url: str) -> bool:
        """Custom LLM 서버 상태 확인"""
        try:
            health_url = f"{model_url.rstrip('/')}/health"
            response = await self._client.get(health_url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Custom LLM health check failed: {e}")
            return False
    
    async def get_available_models(self, model_url: str) -> list[str]:
        """사용 가능한 모델 목록 조회"""
        try:
            models_url = f"{model_url.rstrip('/')}/v1/models"
            response = await self._client.get(models_url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
    
    async def create_custom_vendor(self) -> Optional[CompletionVendor]:
        """Custom LLM 벤더 생성"""
        if not self._settings.CUSTOM_LLM_URL:
            return None
        
        # 헬스체크
        if not await self.check_health(self._settings.CUSTOM_LLM_URL):
            logger.warning("Custom LLM server is not healthy")
            return None
        
        # 사용 가능한 모델 조회
        available_models = await self.get_available_models(self._settings.CUSTOM_LLM_URL)
        
        if not available_models:
            logger.warning("No available models found")
            return None
        
        # 첫 번째 모델을 기본으로 사용
        model = LLMCompletionModel(
            model_name="custom-llm",
            model_url=self._settings.CUSTOM_LLM_URL,
            tool_calling=False,  # Custom LLM은 일반적으로 tool calling 미지원
            temperature=self._settings.DEFAULT_TEMPERATURE
        )
        
        return CompletionVendor(
            vendor_name="Custom",
            model_list=[model],
            api_key_required=bool(self._settings.CUSTOM_LLM_API_KEY)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()