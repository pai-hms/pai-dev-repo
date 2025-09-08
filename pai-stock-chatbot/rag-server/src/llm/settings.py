# rag-server/src/llm/settings.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Dict, Any
from .domains import CompletionModelName, LLMConfig, CompletionVendor, LLMCompletionModel

class LLMSettings(BaseSettings):
    """LLM 관련 설정 - 중앙화된 설정 관리"""
    
    # === OpenAI 설정 (기존 호환성 유지) ===
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"  # 기존 필드 유지
    OPENAI_TEMPERATURE: float = 0.1      # 기존 필드 유지
    
    # === Custom LLM 설정 ===
    CUSTOM_LLM_URL: str = ""
    CUSTOM_LLM_API_KEY: str = ""
    
    # === 기본 모델 설정 ===
    DEFAULT_MAX_TOKENS: int = 1000
    
    # === 시스템 프롬프트 ===
    SYSTEM_PROMPT: str = """당신은 주식 정보와 계산을 도와주는 AI 어시스턴트입니다."""

    class Config:
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        case_sensitive = True
        extra = "ignore"  # 추가 필드 무시 (오류 방지)
    
    @property
    def default_model(self) -> CompletionModelName:
        """기본 모델 반환 (기존 OPENAI_MODEL 사용)"""
        return self.OPENAI_MODEL
    
    @property
    def default_temperature(self) -> float:
        """기본 온도 반환 (기존 OPENAI_TEMPERATURE 사용)"""
        return self.OPENAI_TEMPERATURE
    
    def get_llm_config(self) -> LLMConfig:
        """LLM 설정 객체 생성"""
        return LLMConfig(
            default_model=self.default_model,
            system_prompt=self.SYSTEM_PROMPT,
            vendors=self._create_vendors()
        )
    
    def _create_vendors(self) -> list[CompletionVendor]:
        """사용 가능한 벤더 목록 생성"""
        vendors = []
        
        # OpenAI 벤더
        if self.OPENAI_API_KEY:
            openai_models = [
                LLMCompletionModel("gpt-3.5-turbo", "", True, self.default_temperature),
                LLMCompletionModel("gpt-4o-mini", "", True, self.default_temperature),
                LLMCompletionModel("gpt-4o", "", True, self.default_temperature),
            ]
            vendors.append(CompletionVendor("OpenAI", openai_models, True))
        
        # Custom LLM 벤더
        if self.CUSTOM_LLM_URL:
            custom_models = [
                LLMCompletionModel("custom-llm", self.CUSTOM_LLM_URL, False, self.default_temperature)
            ]
            vendors.append(CompletionVendor("Custom", custom_models, bool(self.CUSTOM_LLM_API_KEY)))
        
        return vendors

# 싱글톤 인스턴스
settings = LLMSettings()