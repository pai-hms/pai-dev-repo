# rag-server/src/llm/container.py
from dependency_injector import containers, providers
from .service import LLMService
from .settings import LLMSettings
from .custom_llm import CustomLLMService

class LLMContainer(containers.DeclarativeContainer):
    """LLM 모듈 DI Container"""
    
    # === 설정 ===
    settings = providers.Singleton(LLMSettings)
    
    # === 서비스 ===
    custom_llm_service = providers.Factory(
        CustomLLMService,
        settings=settings
    )
    
    llm_service = providers.Singleton(
        LLMService,
        settings=settings
    )

def create_llm_container() -> LLMContainer:
    """LLM Container 생성"""
    return LLMContainer()