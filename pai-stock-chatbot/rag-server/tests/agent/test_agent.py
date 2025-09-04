# tests/agent/test_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.service import AgentService
from src.agent.state import AgentState


class TestAgentService:
    """AgentService 테스트"""

    @pytest.fixture
    def agent_service(self, mock_llm_service):
        """AgentService 인스턴스"""
        mock_tools = [MagicMock()]
        return AgentService(llm_service=mock_llm_service, tools=mock_tools)

    def test_agent_service_initialization(self, mock_llm_service):
        """AgentService 초기화 테스트"""
        # given
        tools = [MagicMock(), MagicMock()]
        
        # when
        agent_service = AgentService(llm_service=mock_llm_service, tools=tools)
        
        # then
        assert agent_service._llm_service == mock_llm_service
        assert agent_service._tools == tools
        assert agent_service._llm_with_tools is None  # 지연 초기화

    def test_get_llm_with_tools_lazy_initialization(self, agent_service):
        """LLM with tools 지연 초기화 테스트"""
        # given
        mock_llm_with_tools = MagicMock()
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        
        # when
        result1 = agent_service._get_llm_with_tools()
        result2 = agent_service._get_llm_with_tools()
        
        # then
        assert result1 == mock_llm_with_tools
        assert result2 == mock_llm_with_tools
        # get_llm_with_tools는 한 번만 호출되어야 함
        agent_service._llm_service.get_llm_with_tools.assert_called_once()

    def test_process_state(self, agent_service):
        """상태 처리 테스트"""
        # given
        mock_messages = [HumanMessage(content="테스트 메시지")]
        state = AgentState(messages=mock_messages)
        
        mock_prepared_messages = [HumanMessage(content="준비된 메시지")]
        mock_llm_with_tools = MagicMock()
        mock_result = AIMessage(content="AI 응답")
        
        agent_service._llm_service.prepare_messages.return_value = mock_prepared_messages
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        mock_llm_with_tools.invoke.return_value = mock_result
        
        # when
        result = agent_service.process_state(state)
        
        # then
        assert result == mock_result
        agent_service._llm_service.prepare_messages.assert_called_once_with(mock_messages)
        mock_llm_with_tools.invoke.assert_called_once_with(mock_prepared_messages)

    def test_get_tools(self, agent_service):
        """도구 목록 반환 테스트"""
        # when
        tools = agent_service.get_tools()
        
        # then
        assert tools == agent_service._tools

    def test_process_state_with_empty_messages(self, agent_service):
        """빈 메시지로 상태 처리 테스트"""
        # given
        state = AgentState(messages=[])
        
        mock_prepared_messages = []
        mock_llm_with_tools = MagicMock()
        mock_result = AIMessage(content="기본 응답")
        
        agent_service._llm_service.prepare_messages.return_value = mock_prepared_messages
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        mock_llm_with_tools.invoke.return_value = mock_result
        
        # when
        result = agent_service.process_state(state)
        
        # then
        assert result == mock_result
        agent_service._llm_service.prepare_messages.assert_called_once_with([])

    def test_process_state_with_multiple_messages(self, agent_service):
        """여러 메시지로 상태 처리 테스트"""
        # given
        messages = [
            HumanMessage(content="첫 번째 메시지"),
            AIMessage(content="AI 응답"),
            HumanMessage(content="두 번째 메시지")
        ]
        state = AgentState(messages=messages)
        
        mock_prepared_messages = messages  # 준비된 메시지가 동일하다고 가정
        mock_llm_with_tools = MagicMock()
        mock_result = AIMessage(content="최종 AI 응답")
        
        agent_service._llm_service.prepare_messages.return_value = mock_prepared_messages
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        mock_llm_with_tools.invoke.return_value = mock_result
        
        # when
        result = agent_service.process_state(state)
        
        # then
        assert result == mock_result
        agent_service._llm_service.prepare_messages.assert_called_once_with(messages)


@pytest.mark.asyncio
class TestAgentServiceErrorHandling:
    """AgentService 에러 처리 테스트"""

    @pytest.fixture
    def agent_service(self, mock_llm_service):
        """AgentService 인스턴스"""
        mock_tools = [MagicMock()]
        return AgentService(llm_service=mock_llm_service, tools=mock_tools)

    def test_process_state_llm_service_error(self, agent_service):
        """LLM 서비스 오류 시 처리 테스트"""
        # given
        state = AgentState(messages=[HumanMessage(content="테스트")])
        
        # prepare_messages에서 예외 발생
        agent_service._llm_service.prepare_messages.side_effect = Exception("LLM 서비스 오류")
        
        # when & then
        with pytest.raises(Exception) as exc_info:
            agent_service.process_state(state)
        
        assert "LLM 서비스 오류" in str(exc_info.value)

    def test_process_state_llm_invoke_error(self, agent_service):
        """LLM invoke 오류 시 처리 테스트"""
        # given
        state = AgentState(messages=[HumanMessage(content="테스트")])
        
        mock_prepared_messages = [HumanMessage(content="준비된 메시지")]
        mock_llm_with_tools = MagicMock()
        
        agent_service._llm_service.prepare_messages.return_value = mock_prepared_messages
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        mock_llm_with_tools.invoke.side_effect = Exception("LLM invoke 오류")
        
        # when & then
        with pytest.raises(Exception) as exc_info:
            agent_service.process_state(state)
        
        assert "LLM invoke 오류" in str(exc_info.value)

    def test_get_llm_with_tools_error(self, agent_service):
        """get_llm_with_tools 오류 시 처리 테스트"""
        # given
        agent_service._llm_service.get_llm_with_tools.side_effect = Exception("도구 바인딩 오류")
        
        # when & then
        with pytest.raises(Exception) as exc_info:
            agent_service._get_llm_with_tools()
        
        assert "도구 바인딩 오류" in str(exc_info.value)


@pytest.mark.asyncio 
class TestAgentServiceIntegration:
    """AgentService 통합 테스트"""

    @pytest.fixture
    def agent_service_with_real_tools(self, mock_llm_service):
        """실제 도구들과 함께하는 AgentService"""
        # 실제 agent 도구 객체들을 사용 (stock 모듈 대신)
        from src.agent.tools import get_agent_tools
        
        tools = get_agent_tools()
        
        return AgentService(llm_service=mock_llm_service, tools=tools)

    def test_agent_service_with_real_tools(self, agent_service_with_real_tools):
        """실제 도구들과 함께 AgentService 테스트"""
        # given
        service = agent_service_with_real_tools
        
        # when & then: 서비스가 올바르게 초기화되었는지 확인
        assert service is not None
        assert len(service.tools) == 2  # get_stock_price, calculator
        assert service.tools[0].name == "get_stock_price"
        assert service.tools[1].name == "calculator"


# === Mock 기반 통합 테스트 ===
@pytest.mark.asyncio
class TestAgentServiceMockIntegration:
    """Mock 기반 AgentService 통합 테스트"""

    async def test_complete_agent_workflow(self, mock_llm_service):
        """완전한 에이전트 워크플로우 테스트"""
        # given: 복잡한 시나리오 설정
        tools = [MagicMock(name="get_stock_price"), MagicMock(name="calculator")]
        agent_service = AgentService(llm_service=mock_llm_service, tools=tools)
        
        # 대화 시나리오
        conversation = [
            HumanMessage(content="안녕하세요"),
            AIMessage(content="안녕하세요! 무엇을 도와드릴까요?"),
            HumanMessage(content="AAPL 주가를 알려주고 100주의 가치를 계산해주세요")
        ]
        
        state = AgentState(messages=conversation)
        
        # Mock 설정
        mock_prepared_messages = conversation
        mock_llm_with_tools = MagicMock()
        mock_final_result = AIMessage(content="AAPL 주가는 $150이고, 100주의 가치는 $15,000입니다.")
        
        agent_service._llm_service.prepare_messages.return_value = mock_prepared_messages
        agent_service._llm_service.get_llm_with_tools.return_value = mock_llm_with_tools
        mock_llm_with_tools.invoke.return_value = mock_final_result
        
        # when
        result = agent_service.process_state(state)
        
        # then
        assert result == mock_final_result
        agent_service._llm_service.prepare_messages.assert_called_once_with(conversation)
        mock_llm_with_tools.invoke.assert_called_once_with(mock_prepared_messages)
        
        # 도구들이 제대로 설정되었는지 확인
        assert len(agent_service.get_tools()) == 2
