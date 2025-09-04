# rag-server/src/chatbot/service.py
from typing import AsyncGenerator, Optional, Dict, List
from datetime import datetime
from langchain_core.messages import HumanMessage
import logging

from src.chat_session.service import ChatSessionService
from .repository import ChatbotConfigRepository

logger = logging.getLogger(__name__)

class ChatbotService:
    """챗봇 비즈니스 서비스 - 챗봇 로직 전담"""
    
    def __init__(
        self, 
        chat_session_service: ChatSessionService,
        config_repository: ChatbotConfigRepository,
        agent_executor
    ):
        """완전한 의존성 주입"""
        self._session_service = chat_session_service
        self._config_repository = config_repository
        self._agent_executor = agent_executor
        
        if self._agent_executor is None:
            raise ValueError("agent_executor must be provided via DI")
    
    # === 핵심 챗봇 기능 (AI 응답 생성) ===
    async def stream_response(self, thread_id: str, message: str) -> AsyncGenerator[str, None]:
        """스트리밍 응답 - 핵심 챗봇 기능"""
        logger.info(f"Starting stream_response - thread_id: {thread_id}")
        
        try:
            # 세션 준비
            await self._prepare_session(thread_id, message)
            
            # 에이전트 실행 및 응답 스트리밍
            response_generated = False
            async for content in self._execute_agent_stream(thread_id, message):
                if content:
                    await self._session_service.save_message(thread_id, content, "assistant")
                    response_generated = True
                    yield content
            
            # 응답이 없는 경우 기본 응답 제공
            if not response_generated:
                fallback_msg = "죄송합니다. 응답을 생성할 수 없습니다."
                await self._session_service.save_message(thread_id, fallback_msg, "assistant")
                yield fallback_msg
                
        except Exception as e:
            logger.error(f"Error in stream_response: {e}", exc_info=True)
            error_msg = f"오류가 발생했습니다: {str(e)}"
            await self._session_service.save_message(thread_id, error_msg, "assistant")
            yield error_msg
    
    async def _prepare_session(self, thread_id: str, message: str) -> None:
        """세션 준비 및 사용자 메시지 저장"""
        await self._session_service.get_or_create_session(thread_id)
        await self._session_service.save_message(thread_id, message, "user")
        logger.info("Session prepared and user message saved")
    
    async def _execute_agent_stream(self, thread_id: str, message: str) -> AsyncGenerator[str, None]:
        """에이전트 실행 및 컨텐츠 추출"""
        config = {"configurable": {"thread_id": thread_id}}
        
        async for chunk in self._agent_executor.astream(
            {"messages": [HumanMessage(content=message)]}, 
            config=config
        ):
            content = self._extract_content_from_chunk(chunk)
            if content:
                yield content
    
    def _extract_content_from_chunk(self, chunk: Dict) -> Optional[str]:
        """청크에서 컨텐츠 추출"""
        if not isinstance(chunk, dict):
            return None
        
        # messages 키에서 컨텐츠 추출
        if "messages" in chunk:
            for msg in chunk["messages"]:
                if hasattr(msg, 'content') and msg.content:
                    return msg.content
        
        # agent 키에서 컨텐츠 추출
        if "agent" in chunk:
            agent_data = chunk["agent"]
            if isinstance(agent_data, dict) and "messages" in agent_data:
                for msg in agent_data["messages"]:
                    if hasattr(msg, 'content') and msg.content:
                        return msg.content
        
        return None
    
    # === 세션 관리 (Chat Session Service에 위임) ===
    async def get_session_info(self, thread_id: str) -> Optional[Dict]:
        """세션 정보 조회 - Chat Session Service에 위임"""
        return await self._session_service.get_session_info(thread_id)
    
    async def close_session(self, thread_id: str) -> bool:
        """세션 종료 - Chat Session Service에 위임"""
        return await self._session_service.close_session(thread_id)
    
    async def get_all_active_sessions(self) -> List[Dict]:
        """활성 세션 목록 - Chat Session Service에 위임"""
        return await self._session_service.get_all_active_sessions()
    
    # === 설정 관리 (챗봇 전용) ===
    async def get_chatbot_config(self, config_id: str):
        """챗봇 설정 조회"""
        return self._config_repository.get_config(config_id)
    
    async def update_chatbot_config(self, config_id: str, config_data: dict):
        """챗봇 설정 업데이트"""
        return self._config_repository.update_config(config_id, config_data)