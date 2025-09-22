"""
LLM Provider 구현 - 기존 코드 구조 활용
ChatModelProvider 구현 (임베딩 기능 제거)
"""
import httpx
import tiktoken
from typing import Any, Callable, Dict, List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI




class ChatModelProvider:
    """요청 단위로 모델 키를 받아 적절한 LLM 인스턴스를 돌려주는 Provider.

    - httpx.AsyncClient를 공유(커넥션 풀 재사용)
    - 필요 시 모델 인스턴스 캐싱(벤더/모델 조합별)
    """
    def __init__(self, settings, http_client: httpx.AsyncClient):
        self.settings = settings
        self.async_client = http_client
        self.cache: Dict[str, BaseChatModel] = {}

    @property
    def default_key(self) -> str:
        return getattr(self.settings, 'DEFAULT_MODEL_KEY', 'gemini-2.5-flash-lite')

    def get(self, key: str) -> BaseChatModel:
        """모델 키로 인스턴스 반환. 존재하지 않으면 생성 후 캐시."""
        if key in self.cache:
            return self.cache[key]

        # 키 → 벤더/모델 매핑 규칙 (OpenAI와 Google만 지원)
        if key == "gpt-4o-mini":
            model = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=getattr(self.settings, 'OPENAI_API_KEY', ''),
                temperature=0,
                max_retries=2,
                http_async_client=self.async_client,
            )
        elif key == "gemini-2.5-flash-lite":
            # Google Gemini
            model = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=getattr(self.settings, 'GOOGLE_API_KEY', ''),
                temperature=0.1,
                max_tokens=2000,
            )
        else:
            raise KeyError(f"Unknown model key: {key}. Supported models: gpt-4o-mini, gpt-4o, gemini-2.5-flash-lite")

        self.cache[key] = model
        return model
    
    
    def load_llm_token_count_func(self, model_key: str) -> Callable[[str], int]:
        """
        LLM 모델별 토큰 개수 계산 함수를 로드합니다. (OpenAI와 Google만 지원)
        """
        if model_key in ["gpt-4o-mini", "gpt-4o"]:
            # OpenAI GPT 모델들
            encoding = tiktoken.get_encoding("cl100k_base")
            return lambda x: len(encoding.encode(x))
        elif model_key == "gemini-2.5-flash-lite":
            # Gemini - 기본 토크나이저 사용
            encoding = tiktoken.get_encoding("cl100k_base")
            return lambda x: len(encoding.encode(x))
        else:
            # 기본값: OpenAI 토크나이저 사용
            encoding = tiktoken.get_encoding("cl100k_base")
            return lambda x: len(encoding.encode(x))

    async def aclose(self):
        """리소스 정리"""
        if hasattr(self.async_client, 'aclose'):
            await self.async_client.aclose()


