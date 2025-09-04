# rag-server/webapp/routers/chat.py
import json
import logging
from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse

from src.exceptions import (
    SessionNotFoundException,
    ChatbotServiceException,
    InvalidRequestException
)
from webapp.dtos import (
    ChatRequest,
    SessionInfoDTO,
    SessionResponseDTO,
    ActiveSessionsDTO
)
from webapp.dependency import get_chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/stream",
    summary="채팅 스트리밍",
    description="사용자 메시지를 받아 실시간으로 AI 응답을 스트리밍합니다.",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat_stream(
    request: ChatRequest,
    chatbot_service = Depends(get_chatbot_service)
):
    """채팅 스트리밍"""
    if not request.message.strip():
        raise InvalidRequestException("메시지가 비어있습니다")
    
    def _format_chunk(chunk) -> str:
        """청크 데이터 포맷팅"""
        if isinstance(chunk, str):
            return chunk
        
        try:
            if hasattr(chunk, 'model_dump_json'):
                return chunk.model_dump_json() + "\n"
            return json.dumps({"content": str(chunk)}, ensure_ascii=False) + "\n"
        except Exception:
            return str(chunk)
    
    async def answer_generator():
        try:
            async for chunk in chatbot_service.stream_response(request.thread_id, request.message):
                yield _format_chunk(chunk)
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(answer_generator(), media_type="text/event-stream")

@router.get(
    "/sessions/{thread_id}",
    response_model=SessionInfoDTO,
    summary="세션 정보 조회"
)
async def get_session_info(
    thread_id: str = Path(..., example="thread_123"),
    chatbot_service = Depends(get_chatbot_service)
) -> SessionInfoDTO:
    """세션 정보 조회"""
    try:
        info = await chatbot_service.get_session_info(thread_id)
        if info:
            return SessionInfoDTO(**info)
        raise SessionNotFoundException(f"세션 {thread_id}을 찾을 수 없습니다")
    except SessionNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Session info error: {e}")
        raise ChatbotServiceException(f"세션 정보 조회 중 오류: {str(e)}")

@router.delete(
    "/sessions/{thread_id}",
    response_model=SessionResponseDTO,
    summary="세션 종료"
)
async def close_session(
    thread_id: str = Path(..., example="thread_123"),
    chatbot_service = Depends(get_chatbot_service)
) -> SessionResponseDTO:
    """세션 종료"""
    try:
        success = await chatbot_service.close_session(thread_id)
        if success:
            return SessionResponseDTO(
                message=f"세션 {thread_id}이 종료되었습니다",
                thread_id=thread_id
            )
        else:
            raise SessionNotFoundException(f"세션 {thread_id}을 찾을 수 없습니다")
    except SessionNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Session close error: {e}")
        raise ChatbotServiceException(f"세션 종료 중 오류: {str(e)}")

@router.get(
    "/sessions",
    response_model=ActiveSessionsDTO,
    summary="활성 세션 목록"
)
async def get_active_sessions(
    chatbot_service = Depends(get_chatbot_service)
) -> ActiveSessionsDTO:
    """활성 세션 목록"""
    try:
        sessions = await chatbot_service.get_all_active_sessions()
        return ActiveSessionsDTO(
            sessions=sessions or [],
            total_count=len(sessions) if sessions else 0
        )
    except Exception as e:
        logger.error(f"Active sessions error: {e}")
        raise ChatbotServiceException(f"활성 세션 조회 중 오류: {str(e)}")