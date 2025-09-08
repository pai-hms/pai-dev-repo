# tests/chatbot/test_domains.py
import pytest
from src.chatbot.domains import ChatbotConfig


class TestChatbotConfig:
    """ChatbotConfig 도메인 객체 테스트"""

    def test_chatbot_config_creation(self):
        """ChatbotConfig 생성 테스트"""
        # given
        config = ChatbotConfig(
            chatbot_id="test_bot",
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
            system_prompt="Test prompt"
        )
        
        # then
        assert config.chatbot_id == "test_bot"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.system_prompt == "Test prompt"
        assert config.tools_enabled is True  # 기본값
        assert config.metadata == {}  # __post_init__ 효과

    def test_chatbot_config_post_init_metadata(self):
        """ChatbotConfig __post_init__ 메타데이터 초기화 테스트"""
        # when
        config = ChatbotConfig(
            chatbot_id="test",
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=500,
            system_prompt="Test",
            metadata=None
        )
        
        # then
        assert config.metadata == {}

    def test_chatbot_config_with_existing_metadata(self):
        """기존 메타데이터가 있는 ChatbotConfig 테스트"""
        # given
        existing_metadata = {"version": "1.0", "feature": "stock"}
        
        # when
        config = ChatbotConfig(
            chatbot_id="test",
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=500,
            system_prompt="Test",
            metadata=existing_metadata
        )
        
        # then
        assert config.metadata == existing_metadata

    def test_chatbot_config_default(self):
        """기본 ChatbotConfig 생성 테스트"""
        # when
        config = ChatbotConfig.default()
        
        # then
        assert config.chatbot_id == "default"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.1
        assert config.max_tokens == 1000
        assert config.system_prompt == "당신은 주식 정보를 도와주는 AI 어시스턴트입니다."
        assert config.tools_enabled is True
        assert config.metadata == {}

    def test_chatbot_config_tools_disabled(self):
        """도구 비활성화된 ChatbotConfig 테스트"""
        # when
        config = ChatbotConfig(
            chatbot_id="no_tools_bot",
            model_name="gpt-4o-mini",
            temperature=0.5,
            max_tokens=800,
            system_prompt="No tools bot",
            tools_enabled=False
        )
        
        # then
        assert config.tools_enabled is False

    def test_chatbot_config_custom_values(self):
        """커스텀 값들로 ChatbotConfig 테스트"""
        # given
        custom_metadata = {
            "category": "finance",
            "version": "2.0",
            "features": ["stocks", "calculator"]
        }
        
        # when
        config = ChatbotConfig(
            chatbot_id="finance_bot",
            model_name="gpt-4o",
            temperature=0.3,
            max_tokens=2000,
            system_prompt="당신은 금융 전문가입니다.",
            tools_enabled=True,
            metadata=custom_metadata
        )
        
        # then
        assert config.chatbot_id == "finance_bot"
        assert config.model_name == "gpt-4o"
        assert config.temperature == 0.3
        assert config.max_tokens == 2000
        assert config.system_prompt == "당신은 금융 전문가입니다."
        assert config.tools_enabled is True
        assert config.metadata == custom_metadata