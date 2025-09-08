# rag-server/src/llm/service.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Optional, Dict, Any

from .settings import LLMSettings
from .domains import CompletionModelName, LLMConfig, CompletionVendor
from .custom_llm import CustomLLMService

class LLMService:
    """LLM 비즈니스 서비스"""
    
    def __init__(
        self, 
        settings: LLMSettings,
        custom_llm_service: CustomLLMService
    ):
        """완전한 의존성 주입 - 기본값 제거"""
        self._settings = settings
        self._config = self._settings.get_llm_config()
        self._models_cache: Dict[str, BaseChatModel] = {}
        self._custom_llm_service = custom_llm_service
    
    async def get_available_models(self) -> list[CompletionVendor]:
        """사용 가능한 모든 모델 목록 반환"""
        vendors = self._config.vendors.copy()
        
        # Custom LLM 벤더 동적 추가
        async with self._custom_llm_service as custom_service:
            custom_vendor = await custom_service.create_custom_vendor()
            if custom_vendor:
                vendors.append(custom_vendor)
        
        return vendors
    
    def _create_openai_model(self, model_name: str, api_key: str, base_url: Optional[str] = None) -> BaseChatModel:
        """OpenAI 호환 모델 생성 헬퍼 메서드"""
        kwargs = {
            "model": model_name,
            "openai_api_key": api_key,
            "temperature": self._settings.default_temperature,
            "max_tokens": self._settings.DEFAULT_MAX_TOKENS
        }
        
        if base_url:
            kwargs["openai_api_base"] = base_url
            
        return ChatOpenAI(**kwargs)
    
    def create_chat_model_sync(self, model_name: CompletionModelName = None) -> BaseChatModel:
        """동기 버전 채팅 모델 생성 - 통합 및 최적화"""
        model_name = model_name or self._config.default_model
        
        # 캐시 확인
        if model_name in self._models_cache:
            return self._models_cache[model_name]
        
        # 모델 타입별 생성 로직
        if self._is_openai_model(model_name):
            model = self._create_openai_model(
                model_name=model_name,
                api_key=self._settings.OPENAI_API_KEY
            )
        elif self._settings.CUSTOM_LLM_URL:
            model = self._create_openai_model(
                model_name="custom-model",
                api_key=self._settings.CUSTOM_LLM_API_KEY or "dummy",
                base_url=f"{self._settings.CUSTOM_LLM_URL}/v1"
            )
        else:
            # 기본 모델
            model = self._create_openai_model(
                model_name="gpt-4o-mini",
                api_key=self._settings.OPENAI_API_KEY or "dummy_key"
            )
        
        self._models_cache[model_name] = model
        return model
    
    def _is_openai_model(self, model_name: str) -> bool:
        """OpenAI 모델인지 확인"""
        return (model_name.startswith("gpt") or 
                model_name in ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"])
    
    async def create_chat_model(self, model_name: CompletionModelName = None) -> BaseChatModel:
        """비동기 버전 채팅 모델 생성"""
        return self.create_chat_model_sync(model_name)
    
    def get_llm_with_tools(self, tools, model_name: CompletionModelName = None):
        """도구 바인딩된 LLM 반환 - 동기 버전 사용"""
        model = self.create_chat_model_sync(model_name)
        return model.bind_tools(tools)
    
    def get_streaming_llm_with_tools(self, tools, model_name: CompletionModelName = None):
        """스트리밍용 도구 바인딩된 LLM 반환"""
        model = self.create_chat_model_sync(model_name)
        # 스트리밍을 위해 streaming=True 설정
        if hasattr(model, 'streaming'):
            model.streaming = True
        return model.bind_tools(tools)
    
    def prepare_messages(self, messages):
        """시스템 메시지 추가"""
        system_msg = SystemMessage(content=self._config.system_prompt)
        return [system_msg] + messages