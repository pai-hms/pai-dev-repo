# api/v1/chat.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.chatbot.services import chatbot_service

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
    try:
        return StreamingResponse(
            chatbot_service.stream_response(request.message, request.thread_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 오류: {str(e)}")

@router.get("/session/{thread_id}")
async def get_session_info(
    thread_id: str,
    chatbot_service = Depends(get_chatbot_service)
) -> Optional[SessionInfoResponse]:
    """세션 정보 조회"""
    info = await chatbot_service.get_session_info(thread_id)
    if info:
        return SessionInfoResponse(**info)
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

@router.delete("/session/{thread_id}")
async def close_session(
    thread_id: str,
    chatbot_service = Depends(get_chatbot_service)
):
    """세션 종료"""
    success = await chatbot_service.close_session(thread_id)
    if success:
        return {"message": f"세션 {thread_id}이 종료되었습니다"}
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

@router.get("/sessions/active")
async def get_active_sessions(
    chatbot_service = Depends(get_chatbot_service)
):
    """활성 세션 목록 조회"""
    return await chatbot_service.get_all_active_sessions()
