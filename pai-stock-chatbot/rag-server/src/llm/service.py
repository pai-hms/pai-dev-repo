# rag-server/src/llm/service.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Optional, Dict, Any

from .settings import LLMSettings
from .domains import CompletionModelName, LLMConfig, CompletionVendor
from .custom_llm import CustomLLMService

class LLMService:
    """LLM 비즈니스 서비스 - Factory 패턴 적용"""
    
    def __init__(self, settings: LLMSettings = None):
        from .settings import settings as default_settings
        self._settings = settings or default_settings
        self._config = self._settings.get_llm_config()
        self._models_cache: Dict[str, BaseChatModel] = {}
        self._custom_llm_service = CustomLLMService(self._settings)
    
    async def get_available_models(self) -> list[CompletionVendor]:
        """사용 가능한 모든 모델 목록 반환"""
        vendors = self._config.vendors.copy()
        
        # Custom LLM 벤더 동적 추가
        async with self._custom_llm_service as custom_service:
            custom_vendor = await custom_service.create_custom_vendor()
            if custom_vendor:
                vendors.append(custom_vendor)
        
        return vendors
    
    async def create_chat_model(self, model_name: CompletionModelName = None) -> BaseChatModel:
        """채팅 모델 생성 - Factory 패턴"""
        model_name = model_name or self._config.default_model
        
        # 캐시 확인
        if model_name in self._models_cache:
            return self._models_cache[model_name]
        
        # 모델 생성
        model = await self._create_model_instance(model_name)
        self._models_cache[model_name] = model
        return model
    
    async def _create_model_instance(self, model_name: CompletionModelName) -> BaseChatModel:
        """모델 인스턴스 생성"""
        if model_name in ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]:
            return self._create_openai_model(model_name)
        elif model_name == "custom-llm":
            return await self._create_custom_model()
        else:
            raise ValueError(f"Unsupported model: {model_name}")
    
    def _create_openai_model(self, model_name: str) -> ChatOpenAI:
        """OpenAI 모델 생성"""
        if not self._settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        return ChatOpenAI(
            model=model_name,
            temperature=self._settings.OPENAI_TEMPERATURE,  # 기존 필드 사용
            max_tokens=self._settings.DEFAULT_MAX_TOKENS,
            api_key=self._settings.OPENAI_API_KEY
        )
    
    async def _create_custom_model(self) -> ChatOpenAI:
        """Custom LLM 모델 생성"""
        if not self._settings.CUSTOM_LLM_URL:
            raise ValueError("CUSTOM_LLM_URL이 설정되지 않았습니다.")
        
        # 사용 가능한 모델 확인
        async with self._custom_llm_service as custom_service:
            available_models = await custom_service.get_available_models(
                self._settings.CUSTOM_LLM_URL
            )
            
            if not available_models:
                raise ValueError("사용 가능한 Custom LLM 모델이 없습니다.")
            
            # OpenAI 호환 API 사용
            return ChatOpenAI(
                model=available_models[0],  # 첫 번째 모델 사용
                openai_api_key=self._settings.CUSTOM_LLM_API_KEY or "dummy",
                openai_api_base=f"{self._settings.CUSTOM_LLM_URL}/v1",
                temperature=self._settings.OPENAI_TEMPERATURE,  # 기존 필드 사용
                max_tokens=self._settings.DEFAULT_MAX_TOKENS
            )
    
    def get_llm_with_tools(self, tools, model_name: CompletionModelName = None):
        """도구 바인딩된 LLM 반환 - 기존 호환성 유지"""
        import asyncio
        model = asyncio.run(self.create_chat_model(model_name))
        return model.bind_tools(tools)
    
    def prepare_messages(self, messages):
        """시스템 메시지 추가"""
        system_msg = SystemMessage(content=self._config.system_prompt)
        return [system_msg] + messages