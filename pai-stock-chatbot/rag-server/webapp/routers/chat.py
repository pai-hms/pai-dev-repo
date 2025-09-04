# rag-server/webapp/routers/chat.py
import sys
import os
import json
import logging

# rag-server 폴더를 Python 경로에 추가
rag_server_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, rag_server_root)

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.chatbot.services import chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: str

class SessionInfoResponse(BaseModel):
    thread_id: str
    created_at: str
    last_accessed: str
    message_count: int
    active: bool

def get_chatbot_service():
    return chatbot_service

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    chatbot_service = Depends(get_chatbot_service)
):
    """스트리밍 엔드포인트"""
    
    async def answer_generator():
        try:
            async for chunk in chatbot_service.stream_response(request.message, request.thread_id):
                # chunk가 문자열인 경우 (가장 일반적)
                if isinstance(chunk, str):
                    yield chunk
                else:
                    # 객체인 경우 JSON으로 변환
                    try:
                        if hasattr(chunk, 'model_dump_json'):
                            yield chunk.model_dump_json() + "\n"
                        else:
                            yield json.dumps({"content": str(chunk)}, ensure_ascii=False) + "\n"
                    except Exception:
                        yield str(chunk)
                        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(answer_generator(), media_type="text/event-stream")

@router.get("/session/{thread_id}")
async def get_session_info(
    thread_id: str,
    chatbot_service = Depends(get_chatbot_service)
) -> Optional[SessionInfoResponse]:
    """세션 정보 조회"""
    try:
        info = await chatbot_service.get_session_info(thread_id)
        if info:
            return SessionInfoResponse(**info)
        return None
    except Exception as e:
        logger.error(f"Session info error: {e}")
        return None

@router.delete("/session/{thread_id}")
async def close_session(
    thread_id: str,
    chatbot_service = Depends(get_chatbot_service)
):
    """세션 종료"""
    try:
        success = await chatbot_service.close_session(thread_id)
        if success:
            return {"message": f"세션 {thread_id}이 종료되었습니다"}
        else:
            return {"error": "세션을 찾을 수 없습니다"}
    except Exception as e:
        logger.error(f"Session close error: {e}")
        return {"error": "세션 종료 중 오류가 발생했습니다"}

@router.get("/sessions/active")
async def get_active_sessions(
    chatbot_service = Depends(get_chatbot_service)
):
    """활성 세션 목록 조회"""
    try:
        return await chatbot_service.get_all_active_sessions()
    except Exception as e:
        logger.error(f"Active sessions error: {e}")
        return {"error": "활성 세션 조회 중 오류가 발생했습니다"}