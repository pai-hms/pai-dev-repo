# rag-server/src/chatbot/service.py
from typing import AsyncGenerator, Optional
from datetime import datetime  # datetime import 추가
from langchain_core.messages import HumanMessage
import logging
import re

from src.exceptions import InvalidRequestException, ChatbotServiceException, SessionNotFoundException
from src.chat_session.service import ChatSessionService
from .repository import ChatbotConfigRepository
from .domains import ChatbotConfig

logger = logging.getLogger(__name__)

class ChatbotService:
    """챗봇 AI 응답 생성 서비스 - AI 로직 전담"""
    
    def __init__(
        self, 
        chat_session_service: ChatSessionService,  # 세션 관리 위임
        config_repository: ChatbotConfigRepository,
        agent_executor
    ):
        self._session_service = chat_session_service
        self._config_repository = config_repository
        self._agent_executor = agent_executor
        
        if self._agent_executor is None:
            raise ValueError("agent_executor must be provided via DI")
    
    # === 핵심 AI 응답 생성 ===
    async def stream_response(self, session_id: str, message: str) -> AsyncGenerator[str, None]:
        """AI 응답 스트리밍 생성"""
        logger.info(f"Starting AI response - session_id: {session_id}")
        
        # 입력 검증
        self._validate_inputs(session_id, message)
        
        # 세션 확인 또는 자동 생성
        try:
            session = await self._session_service.get_session(session_id)
            logger.info(f"Found existing session: {session_id}")
        except SessionNotFoundException:
            # 세션이 없으면 자동 생성
            logger.info(f"Session not found, creating new session: {session_id}")
            session = await self._session_service.start_new_session(
                title=message[:20] + "..." if len(message) > 20 else message,
                chatbot_id="default"
            )
            # 새로 생성된 세션의 ID를 사용자가 제공한 ID로 업데이트
            session.session_id = session_id
            self._session_service._repository.save_session(session)
        
        # 사용자 메시지 저장
        await self._session_service.save_message(session_id, message, "user")
        
        # 챗봇 설정 로드
        chatbot_config = self._config_repository.get_config(session.chatbot_id)
        
        # AI 응답 생성
        response_generated = False
        async for content in self._execute_agent_stream(session_id, message, chatbot_config):
            if content:
                validated_content = self._validate_content(content)
                # AI 응답 저장 (세션 서비스에 위임)
                await self._session_service.save_message(session_id, validated_content, "assistant")
                response_generated = True
                yield validated_content
        
        if not response_generated:
            fallback_msg = "죄송합니다. 응답을 생성할 수 없습니다."
            await self._session_service.save_message(session_id, fallback_msg, "assistant")
            yield fallback_msg
    
    # === 세션 관리 (Chat Session Service에 완전 위임) ===
    async def start_new_chat(self, title: str, chatbot_id: str = "default") -> str:
        """새 채팅 시작"""
        session = await self._session_service.start_new_session(title, chatbot_id)
        return session.session_id
    
    async def get_session_info(self, session_id: str):
        """세션 정보 조회"""
        session = await self._session_service.get_session(session_id)
        return {
            "session_id": session.session_id,
            "title": session.title,
            "chatbot_id": session.chatbot_id,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "message_count": session.message_count,
            "is_active": session.is_active
        }
    
    async def close_session(self, session_id: str) -> bool:
        """세션 종료"""
        return await self._session_service.close_session(session_id)
    
    async def get_all_active_sessions(self):
        """활성 세션 목록"""
        sessions = await self._session_service.get_active_sessions()
        return [
            {
                "session_id": s.session_id,
                "title": s.title,
                "chatbot_id": s.chatbot_id,
                "last_accessed": s.last_accessed.isoformat(),
                "message_count": s.message_count
            }
            for s in sessions
        ]
    
    # === 챗봇 설정 관리 ===
    async def get_chatbot_config(self, chatbot_id: str) -> ChatbotConfig:
        """챗봇 설정 조회"""
        if not chatbot_id or not chatbot_id.strip():
            raise InvalidRequestException("챗봇 ID가 비어있습니다")
        return self._config_repository.get_config(chatbot_id)
    
    async def update_chatbot_config(self, chatbot_id: str, config_data: dict) -> ChatbotConfig:
        """챗봇 설정 업데이트"""
        if not chatbot_id or not chatbot_id.strip():
            raise InvalidRequestException("챗봇 ID가 비어있습니다")
        if not config_data:
            raise InvalidRequestException("설정 데이터가 비어있습니다")
        return self._config_repository.update_config(chatbot_id, config_data)
    
    # === 내부 Helper 메서드들 ===
    def _validate_inputs(self, session_id: str, message: str) -> None:
        """입력 검증"""
        if not session_id or not session_id.strip():
            raise InvalidRequestException("세션 ID가 비어있습니다")
        
        if not message or not message.strip():
            raise InvalidRequestException("메시지가 비어있습니다")
        
        if len(message.strip()) > 1000:
            raise InvalidRequestException("메시지는 1000자를 초과할 수 없습니다")
        
        if re.search(r'[<>]', message):
            raise InvalidRequestException("허용되지 않는 문자가 포함되어 있습니다")
    
    async def _execute_agent_stream(self, session_id: str, message: str, config: ChatbotConfig) -> AsyncGenerator[str, None]:
        """AI 에이전트 실행"""
        try:
            agent_config = {"configurable": {"thread_id": session_id}}
            
            async for chunk in self._agent_executor.astream(
                {"messages": [HumanMessage(content=message.strip())]}, 
                config=agent_config
            ):
                content = self._extract_content_from_chunk(chunk)
                if content:
                    yield content
                    
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise ChatbotServiceException(f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}")
    
    def _validate_content(self, content: str) -> str:
        """응답 컨텐츠 검증"""
        if not content:
            return content
        
        if len(content) > 5000:
            return content[:4900] + "...\n\n(응답이 너무 길어 일부만 표시됩니다)"
        
        return content.strip()
    
    def _extract_content_from_chunk(self, chunk) -> Optional[str]:
        """청크에서 컨텐츠 추출"""
        if not isinstance(chunk, dict):
            return None
        
        if "messages" in chunk:
            for msg in chunk["messages"]:
                if hasattr(msg, 'content') and msg.content:
                    return msg.content
        
        if "agent" in chunk:
            agent_data = chunk["agent"]
            if isinstance(agent_data, dict) and "messages" in agent_data:
                for msg in agent_data["messages"]:
                    if hasattr(msg, 'content') and msg.content:
                        return msg.content
        
        return None