# app/api/v1/chat.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ...core.session_manager import session_manager

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

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """개선된 멀티세션 스트리밍 엔드포인트"""
    try:
        return StreamingResponse(
            session_manager.stream_chat(request.message, request.thread_id),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 오류: {str(e)}")

@router.get("/session/{thread_id}")
async def get_session_info(thread_id: str) -> Optional[SessionInfoResponse]:
    """세션 정보 조회"""
    info = await session_manager.get_session_info(thread_id)
    if info:
        return SessionInfoResponse(**info)
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

@router.delete("/session/{thread_id}")
async def close_session(thread_id: str):
    """세션 종료"""
    success = await session_manager.close_session(thread_id)
    if success:
        return {"message": f"세션 {thread_id}이 종료되었습니다"}
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

@router.get("/sessions/active")
async def get_active_sessions():
    """활성 세션 목록 조회"""
    active_sessions = []
    for thread_id in session_manager._sessions.keys():
        info = await session_manager.get_session_info(thread_id)
        if info:
            active_sessions.append(info)
    return {"active_sessions": active_sessions, "count": len(active_sessions)}