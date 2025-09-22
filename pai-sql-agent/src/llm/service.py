"""
통합 LLM 서비스 - 모든 LLM 관련 기능을 담당
통계청 및 SGIS 데이터 분석용 LLM 모델 관리 서비스
"""
import asyncio
import logging
from typing import Optional, List

from pydantic_settings import BaseSettings
from pydantic import Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from src.agent.settings import get_settings

logger = logging.getLogger(__name__)


class LLMConfig(BaseSettings):
    """
    LLM 설정 (간소화) - 실제 사용되는 필드만 유지
    """
    
    # 필수 설정
    provider: str = Field(default="google", description="LLM 프로바이더 (openai, google)")
    model_name: str = Field(default="gemini-2.5-flash-lite", description="사용할 LLM 모델명")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM 창의성 수준")
    max_tokens: int = Field(default=2000, gt=0, description="최대 토큰 수")
    
    # 성능 설정
    max_retries: int = Field(default=3, ge=0, description="최대 재시도 횟수")
    request_timeout: float = Field(default=30.0, gt=0.0, description="요청 타임아웃 (초)")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p 샘플링 값")
    
    # OpenAI 전용 설정
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="빈도 패널티 (OpenAI)")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="존재 패널티 (OpenAI)")
    
    class Config:
        env_prefix = "LLM_"
        case_sensitive = False


# LLMResponse 클래스 제거됨 - 직접 LangChain 응답 사용


class LLMService:
    """
    통합 LLM 서비스
    
    역할:
    - LLM 모델 관리
    - 통계 데이터 분석용 프롬프트 처리
    - 스트리밍 및 일반 응답 지원
    - 에러 처리 및 재시도 로직
    """
    
    def __init__(self, chat_model_provider=None, settings=None, config: Optional[LLMConfig] = None):
        """
        LLM 서비스 초기화 - dependency-injector 호환
        
        Args:
            chat_model_provider: 채팅 모델 프로바이더 (DI)
            settings: 설정 객체 (DI)
            config: LLM 설정 (None이면 기본 설정 사용)
        """
        self.config = config or LLMConfig()
        self.settings = settings or get_settings()
        self._chat_model_provider = chat_model_provider
        self._llm: Optional[BaseChatModel] = None
        self._initialized = chat_model_provider is not None
        
        logger.info(f"LLM 서비스 초기화: {self.config.model_name}")
    
    @property
    def llm(self) -> BaseChatModel:
        """LLM 모델 인스턴스 (지연 초기화)"""
        if self._llm is None:
            if self._chat_model_provider:
                # DI를 통한 모델 생성
                self._llm = self._chat_model_provider.get_chat_model(
                    provider=self.config.provider,
                    model_name=self.config.model_name
                )
            else:
                # 기존 방식으로 모델 생성
                self._llm = self._create_llm()
        return self._llm
    
    def _create_llm(self) -> BaseChatModel:
        """LLM 모델 생성"""
        try:
            # 빈 문자열이나 None인 경우 기본값으로 설정
            provider = self.config.provider.lower().strip() if self.config.provider else "google"
            model_name = self.config.model_name.strip() if self.config.model_name else "gemini-2.5-flash-lite"
            
            logger.info(f"사용할 Provider: '{provider}', Model: '{model_name}'")
            
            if provider == "google":
                # Google Gemini 모델 생성
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.request_timeout,
                    max_retries=self.config.max_retries,
                    top_p=self.config.top_p,
                    google_api_key=self.settings.GOOGLE_API_KEY,
                )
                logger.info(f"Google Gemini 모델 생성: {model_name}")
                
            elif provider == "openai":
                # OpenAI GPT 모델 생성
                llm = ChatOpenAI(
                    model=model_name,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.request_timeout,
                    max_retries=self.config.max_retries,
                    top_p=self.config.top_p,
                    frequency_penalty=self.config.frequency_penalty,
                    presence_penalty=self.config.presence_penalty,
                    openai_api_key=self.settings.OPENAI_API_KEY,
                )
                logger.info(f"OpenAI GPT 모델 생성: {model_name}")
                
            else:
                # 기본값으로 Google Gemini 사용
                logger.warning(f"알 수 없는 프로바이더 '{provider}', Google Gemini로 기본 설정")
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash-lite",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.request_timeout,
                    max_retries=self.config.max_retries,
                    top_p=self.config.top_p,
                    google_api_key=self.settings.GOOGLE_API_KEY,
                )
                logger.info(f"기본 Google Gemini 모델 생성: gemini-2.5-flash-lite")
            
            logger.info(f"LLM 모델 생성 완료: {provider}/{model_name}")
            return llm
            
        except Exception as e:
            logger.error(f"LLM 모델 생성 실패: {e}")
            raise
    
    async def generate(self, messages: List[BaseMessage], **kwargs):
        """LLM 응답 생성 (비스트리밍) - 직접 LangChain 응답 반환"""
        try:
            response = await self.llm.ainvoke(messages, **kwargs)
            return response
            
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            raise
    
# 사용되지 않는 메서드들 제거됨 - 핵심 기능만 유지


# 글로벌 LLM 서비스 인스턴스 (싱글톤)
_llm_service: Optional[LLMService] = None
_lock = asyncio.Lock()


async def get_llm_service(config: Optional[LLMConfig] = None) -> LLMService:
    """
    LLM 서비스 인스턴스 반환 (싱글톤)
    
    Args:
        config: LLM 설정 (첫 번째 호출 시에만 적용)
    
    Returns:
        LLM 서비스 인스턴스
    """
    global _llm_service
    
    if _llm_service is None:
        async with _lock:
            if _llm_service is None:
                _llm_service = LLMService(config)
    
    return _llm_service


