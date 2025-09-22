"""
통합 LLM 서비스 - 모든 LLM 관련 기능을 담당
통계청 및 SGIS 데이터 분석용 LLM 모델 관리 서비스
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass

from pydantic_settings import BaseSettings
from pydantic import Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from src.agent.settings import get_settings

logger = logging.getLogger(__name__)


class LLMConfig(BaseSettings):
    """
    LLM 설정 (pydantic_settings 기반)
    
    통계청 및 SGIS: LLM 모델 설정 관리용 llm 서비스 전용
    환경변수에서 값을 읽어오며, 기본값 제공
    """
    
    # 모델 설정
    provider: str = Field(
        default="google",  # 기본: Google Gemini, 전환시: "openai"
        description="LLM 프로바이더 (openai, google)"
    )
    model_name: str = Field(
        default="gemini-2.5-flash-lite",  # Google 기본값, OpenAI: "gpt-4o-mini"
        description="사용할 LLM 모델명 (gemini-2.5-flash-lite, gpt-4o-mini)"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM 창의성 수준 (0.0-2.0)"
    )
    max_tokens: int = Field(
        default=2000,
        gt=0,
        description="최대 토큰 수"
    )
    streaming: bool = Field(
        default=True,
        description="스트리밍 모드 활성화"
    )
    timeout: int = Field(
        default=60,
        gt=0,
        description="요청 타임아웃 (초)"
    )
    
    # 성능 설정
    max_retries: int = Field(
        default=3,
        ge=0,
        description="최대 재시도 횟수"
    )
    request_timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="개별 요청 타임아웃 (초)"
    )
    
    # 고급 설정
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p 샘플링 값"
    )
    frequency_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="빈도 패널티"
    )
    presence_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="존재 패널티"
    )
    
    class Config:
        env_prefix = "LLM_"  # 환경변수 접두사
        case_sensitive = False


@dataclass
class LLMResponse:
    """LLM 응답 데이터"""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMService:
    """
    통합 LLM 서비스
    
    역할:
    - LLM 모델 관리
    - 통계 데이터 분석용 프롬프트 처리
    - 스트리밍 및 일반 응답 지원
    - 에러 처리 및 재시도 로직
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        LLM 서비스 초기화
        
        Args:
            config: LLM 설정 (None이면 기본 설정 사용)
        """
        self.config = config or LLMConfig()
        self.settings = get_settings()
        self._llm: Optional[BaseChatModel] = None
        
        logger.info(f"LLM 서비스 초기화: {self.config.model_name}")
    
    @property
    def llm(self) -> BaseChatModel:
        """LLM 모델 인스턴스 (지연 초기화)"""
        if self._llm is None:
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
                    streaming=self.config.streaming,
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
    
    async def generate(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> LLMResponse:
        """LLM 응답 생성 (비스트리밍)"""
        try:
            # 수정: streaming 파라미터 제거
            response = await self.llm.ainvoke(messages, **kwargs)
            
            return LLMResponse(
                content=response.content,
                model=self.config.model_name,
                usage=getattr(response, 'usage_metadata', None),
                metadata=getattr(response, 'response_metadata', None)
            )
            
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ):
        """
        LLM 스트리밍 응답 생성
        
        Args:
            messages: 대화 메시지 리스트
            **kwargs: 추가 LLM 파라미터
        
        Yields:
            스트리밍 응답 청크
        """
        try:
            # 스트리밍 활성화
            temp_llm = self.llm.bind(streaming=True, **kwargs)
            
            async for chunk in temp_llm.astream(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"LLM 스트리밍 실패: {e}")
            raise
    
    def create_human_message(self, content: str) -> HumanMessage:
        """사용자 메시지 생성"""
        return HumanMessage(content=content)
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            "model_name": self.config.model_name,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "streaming": self.config.streaming,
            "timeout": self.config.timeout
        }
    
    async def get_model(self, config: Optional[LLMConfig] = None) -> BaseChatModel:
        """
        LLM 모델 인스턴스 반환 (스트리밍 지원)
        """
        if config and config != self.config:
            # 새로운 설정으로 임시 모델 생성
            temp_service = LLMService(config)
            return temp_service.llm
        
        return self.llm
    
    def update_config(self, **kwargs) -> LLMConfig:
        """
        설정 업데이트 (새로운 설정 객체 반환)
        """
        config_dict = self.config.model_dump()
        config_dict.update(kwargs)
        return LLMConfig(**config_dict)
    
    async def test_connection(self) -> bool:
        """LLM 연결 테스트"""
        try:
            test_message = HumanMessage(content="test")
            await self.llm.ainvoke([test_message])
            logger.info("LLM 연결 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"LLM 연결 테스트 실패: {e}")
            return False


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


