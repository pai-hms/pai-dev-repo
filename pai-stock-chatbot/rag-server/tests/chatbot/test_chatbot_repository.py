# tests/chatbot/test_repository.py
import pytest
from src.chatbot.repository import ChatbotConfigRepository
from src.chatbot.domains import ChatbotConfig


class TestChatbotConfigRepository:
    """ChatbotConfigRepository 테스트"""

    @pytest.fixture
    def repository(self):
        """Repository 인스턴스"""
        return ChatbotConfigRepository()

    @pytest.fixture
    def sample_config(self):
        """샘플 설정"""
        return ChatbotConfig(
            chatbot_id="test_bot",
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1500,
            system_prompt="테스트용 봇입니다."
        )

    def test_init_default_config(self, repository):
        """기본 설정 초기화 테스트"""
        # when
        default_config = repository.get_config("default")
        
        # then
        assert default_config.chatbot_id == "default"
        assert default_config.model_name == "gpt-4o-mini"
        assert default_config.temperature == 0.1
        assert default_config.max_tokens == 1000

    def test_get_existing_config(self, repository, sample_config):
        """기존 설정 조회 테스트"""
        # given
        repository.save_config("test_bot", sample_config)
        
        # when
        result = repository.get_config("test_bot")
        
        # then
        assert result.chatbot_id == sample_config.chatbot_id
        assert result.model_name == sample_config.model_name
        assert result.temperature == sample_config.temperature

    def test_get_non_existing_config_returns_default(self, repository):
        """존재하지 않는 설정 조회 시 기본값 반환 테스트"""
        # when
        result = repository.get_config("non_existing_bot")
        
        # then
        assert result.chatbot_id == "default"  # 기본 설정 반환

    def test_save_config(self, repository, sample_config):
        """설정 저장 테스트"""
        # when
        repository.save_config("test_bot", sample_config)
        
        # then
        saved_config = repository.get_config("test_bot")
        assert saved_config.chatbot_id == sample_config.chatbot_id
        assert saved_config.model_name == sample_config.model_name

    def test_update_config(self, repository, sample_config):
        """설정 업데이트 테스트"""
        # given
        repository.save_config("test_bot", sample_config)
        
        # when
        update_data = {
            "temperature": 0.9,
            "max_tokens": 2000,
            "system_prompt": "업데이트된 프롬프트"
        }
        updated_config = repository.update_config("test_bot", update_data)
        
        # then
        assert updated_config.temperature == 0.9
        assert updated_config.max_tokens == 2000
        assert updated_config.system_prompt == "업데이트된 프롬프트"
        # 기존 값은 유지
        assert updated_config.chatbot_id == sample_config.chatbot_id
        assert updated_config.model_name == sample_config.model_name

    def test_update_config_invalid_field(self, repository, sample_config):
        """존재하지 않는 필드 업데이트 테스트"""
        # given
        repository.save_config("test_bot", sample_config)
        
        # when
        update_data = {
            "temperature": 0.8,
            "invalid_field": "should_be_ignored"
        }
        updated_config = repository.update_config("test_bot", update_data)
        
        # then
        assert updated_config.temperature == 0.8
        # invalid_field는 무시되어야 함
        assert not hasattr(updated_config, "invalid_field")

    def test_update_non_existing_config_uses_default(self, repository):
        """존재하지 않는 설정 업데이트 시 기본값 사용 테스트"""
        # when
        update_data = {"temperature": 0.5}
        updated_config = repository.update_config("new_bot", update_data)
        
        # then
        assert updated_config.temperature == 0.5
        assert updated_config.chatbot_id == "default"  # 기본값에서 시작

    def test_multiple_configs(self, repository):
        """여러 설정 관리 테스트"""
        # given
        config1 = ChatbotConfig(
            chatbot_id="bot1",
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000,
            system_prompt="Bot 1"
        )
        config2 = ChatbotConfig(
            chatbot_id="bot2",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="Bot 2"
        )
        
        # when
        repository.save_config("bot1", config1)
        repository.save_config("bot2", config2)
        
        # then
        retrieved_config1 = repository.get_config("bot1")
        retrieved_config2 = repository.get_config("bot2")
        
        assert retrieved_config1.chatbot_id == "bot1"
        assert retrieved_config1.temperature == 0.1
        assert retrieved_config2.chatbot_id == "bot2"
        assert retrieved_config2.temperature == 0.7

    def test_repository_isolation(self, sample_config):
        """Repository 인스턴스 간 격리 테스트"""
        # given
        repo1 = ChatbotConfigRepository()
        repo2 = ChatbotConfigRepository()
        
        # when
        repo1.save_config("test_bot", sample_config)
        
        # then
        assert repo1.get_config("test_bot").chatbot_id == "test_bot"
        # repo2에는 저장되지 않았으므로 default 반환
        assert repo2.get_config("test_bot").chatbot_id == "default"
