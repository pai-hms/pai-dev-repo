# rag-server/src/chatbot/services.py
from langchain_core.messages import HumanMessage
from ..agent.graph import get_agent_executor
from ..chat_session.service import ChatSessionService

class ChatbotService:  # ChatBotService → ChatbotService로 변경
    """통합 챗봇 서비스"""
    
    def __init__(self, session_service=None):
        self._executor = get_agent_executor()
        self._session_service = session_service or ChatSessionService()
    
    async def stream_response(self, thread_id: str, message: str):
        """스트리밍 응답"""
        session = await self._session_service.get_or_create_session(thread_id)
        session.increment_message_count()
        
        try:
            async for event in self._executor.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config={"configurable": {"thread_id": thread_id}},
                version="v1"
            ):
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield content
        except Exception as e:
            yield f"오류가 발생했습니다: {str(e)}"
    
    async def get_session_info(self, thread_id: str):
        """세션 정보 조회"""
        return await self._session_service.get_session_info(thread_id)
    
    async def close_session(self, thread_id: str):
        """세션 종료"""
        return await self._session_service.close_session(thread_id)
    
    async def get_all_active_sessions(self):
        """모든 활성 세션 조회"""
        sessions = self._session_service.get_all_sessions()
        active_sessions = []
        for thread_id, session in sessions.items():
            info = await self._session_service.get_session_info(thread_id)
            if info:
                active_sessions.append(info)
        return {"active_sessions": active_sessions, "count": len(active_sessions)}

# 싱글톤 인스턴스 (DI Container에서 관리하므로 제거 예정)
# chatbot_service = ChatbotService()  # DI Container로 이관