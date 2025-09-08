# rag-server/src/llm/container.py
from dependency_injector import containers, providers
from .service import LLMService
from .settings import LLMSettings
from .custom_llm import CustomLLMService

class LLMContainer(containers.DeclarativeContainer):
    """LLM 모듈 DI Container"""
    
    # === Settings ===
    settings = providers.Singleton(LLMSettings)
    
    # === Custom LLM Service ===
    custom_llm_service = providers.Singleton(
        CustomLLMService,
        settings=settings
    )
    
    # === Main Service ===
    service = providers.Singleton(
        LLMService,
        settings=settings,
        custom_llm_service=custom_llm_service
    )

def create_llm_container() -> LLMContainer:
    return LLMContainer()