import time
import json
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage

from webapp.models import QueryRequest, QueryResponse, StreamChunk, ToolInfo
from src.agent.service import get_unified_agent_service, get_main_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


def safe_json_dumps(obj):
    """안전한 JSON 직렬화 (직렬화할 수 없는 객체 처리)"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON 직렬화 실패: {e}, 객체: {type(obj)}")
        # 직렬화 실패시 안전한 객체로 변환
        safe_obj = {
            "type": getattr(obj, "type", "unknown"),
            "content": str(getattr(obj, "content", obj)),
            "timestamp": getattr(obj, "timestamp", None),
            "error": "직렬화 실패"
        }
        return json.dumps(safe_obj, ensure_ascii=False)


@router.post("/query")
async def query_sql_agent_stream(request: QueryRequest) -> StreamingResponse:
    """
    🌊 통합 스트리밍 SQL Agent (기본 엔드포인트)
    모든 요청이 자동으로 스트리밍으로 처리됩니다
    """
    
    async def generate_unified_stream():
        try:
            # 세션 ID 생성
            session_id = request.session_id or str(uuid.uuid4())
            
            # 스트리밍 모드 결정 (기본값: all)
            stream_mode = getattr(request, 'stream_mode', 'all')
            
            # 통합 에이전트 서비스 가져오기
            agent_service = await get_unified_agent_service()
            
            # 통합 스트리밍 실행
            async for stream_chunk in agent_service.process_request_stream(
                user_input=request.question, 
                thread_id=request.thread_id, 
                session_id=session_id,
                stream_mode=stream_mode,
                request_type=getattr(request, 'request_type', None)
            ):
                # 안전한 JSON 직렬화
                yield f"data: {safe_json_dumps(stream_chunk)}\n\n"
            
            # 스트림 종료 신호
            end_chunk = {
                'type': 'done', 
                'content': '✅ 응답 생성 완료', 
                'session_id': session_id,
                'mode': stream_mode
            }
            yield f"data: {safe_json_dumps(end_chunk)}\n\n"
            
        except Exception as e:
            logger.error(f"통합 스트리밍 오류: {str(e)}")
            error_chunk = {
                'type': 'error', 
                'content': f'❌ 오류: {str(e)}',
                'error': str(e),
                'session_id': request.session_id or str(uuid.uuid4())
            }
            yield f"data: {safe_json_dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_unified_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("/query/stream")
async def query_stream_alias(request: QueryRequest) -> StreamingResponse:
    """
    하위 호환성을 위한 별칭 - 동일한 통합 스트리밍 사용
    """
    return await query_sql_agent_stream(request)


@router.post("/query/realtime-stream")
async def query_realtime_stream_alias(request: QueryRequest) -> StreamingResponse:
    """
    하위 호환성을 위한 별칭 - 동일한 통합 스트리밍 사용
    """
    return await query_sql_agent_stream(request)


@router.post("/query/advanced-stream")
async def query_advanced_stream_alias(request: QueryRequest) -> StreamingResponse:
    """
    하위 호환성을 위한 별칭 - 동일한 통합 스트리밍 사용
    """
    return await query_sql_agent_stream(request)


# ===== 유틸리티 엔드포인트 =====

@router.get("/status")
async def get_agent_status():
    """에이전트 상태 확인"""
    try:
        agent_service = await get_unified_agent_service()
        return {
            "success": True,
            "status": "active",
            "message": "Agent 서비스가 정상 작동 중입니다",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Agent 서비스 오류: {str(e)}",
            "timestamp": time.time()
        }


# ===== 멀티턴 대화 지원 엔드포인트 =====

@router.get("/conversation/{thread_id}/history")
async def get_conversation_history(thread_id: str, limit: int = 10):
    """
    대화 기록 조회 (멀티턴 대화용)
    
    Args:
        thread_id: 대화 스레드 ID
        limit: 조회할 기록 수 (기본 10개)
    """
    try:
        # 메인 에이전트를 통해 SQL 에이전트 서비스 가져오기
        main_agent_service = await get_main_agent_service()
        sql_agent_service = main_agent_service.get_sql_agent_service()
        result = await sql_agent_service.get_conversation_history(thread_id, limit)
        
        return {
            "success": result["success"],
            "message": result.get("message", "대화 기록 조회 완료"),
            "thread_id": thread_id,
            "history": result.get("history", []),
            "count": result.get("count", 0)
        }
        
    except Exception as e:
        logger.error(f"대화 기록 조회 중 오류: {str(e)}")
        return {
            "success": False,
            "message": "대화 기록 조회 중 오류가 발생했습니다",
            "error_message": str(e),
            "thread_id": thread_id,
            "history": [],
            "count": 0
        }


@router.delete("/conversation/{thread_id}")
async def delete_conversation(thread_id: str):
    """
    대화 기록 삭제 (멀티턴 대화용)
    
    Args:
        thread_id: 삭제할 대화 스레드 ID
    """
    try:
        # 메인 에이전트를 통해 SQL 에이전트 서비스 가져오기
        main_agent_service = await get_main_agent_service()
        sql_agent_service = main_agent_service.get_sql_agent_service()
        result = await sql_agent_service.delete_conversation(thread_id)
        
        return {
            "success": result["success"],
            "message": result.get("message", "대화 기록 삭제 완료"),
            "thread_id": thread_id
        }
        
    except Exception as e:
        logger.error(f"대화 기록 삭제 중 오류: {str(e)}")
        return {
            "success": False,
            "message": "대화 기록 삭제 중 오류가 발생했습니다",
            "error_message": str(e),
            "thread_id": thread_id
        }