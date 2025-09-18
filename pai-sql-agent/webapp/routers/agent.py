"""
SQL Agent API 라우터 - 간소화된 버전
"""
import logging
import json
import uuid
import time
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from webapp.models import QueryRequest
from src.agent.service import get_sql_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


def safe_json_dumps(obj):
    """안전한 JSON 직렬화"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"JSON 직렬화 실패: {e}")
        return json.dumps({
            "type": "error",
            "content": f"직렬화 오류: {str(e)}",
            "timestamp": time.time()
        }, ensure_ascii=False)


@router.post("/query")
async def query_sql_agent_stream(request: QueryRequest) -> StreamingResponse:
    """SQL Agent 스트리밍 API"""
    
    async def generate_stream():
        session_id = request.session_id or str(uuid.uuid4())
        
        try:
            logger.info(f"SQL Agent 요청: {request.question[:50]}...")
            
            # SQL Agent 서비스 가져오기
            agent_service = await get_sql_agent_service()
            
            # 스트리밍 처리
            async for chunk in agent_service.process_query_stream(
                question=request.question,
                thread_id=request.thread_id,
                session_id=session_id
            ):
                yield f"data: {safe_json_dumps(chunk)}\n\n"
            
        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            error_chunk = {
                "type": "error",
                "content": f"처리 중 오류가 발생했습니다: {str(e)}",
                "session_id": session_id,
                "timestamp": time.time()
            }
            yield f"data: {safe_json_dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/status")
async def get_agent_status():
    """Agent 상태 확인"""
    try:
        agent_service = await get_sql_agent_service()
        return {
            "success": True,
            "status": "active" if agent_service._initialized else "initializing",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"상태 확인 오류: {e}")
        return {
            "success": False,
            "status": "error",
            "message": str(e),
            "timestamp": time.time()
        }