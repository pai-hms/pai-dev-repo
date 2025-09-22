"""
SQL Agent API 라우터 - DI 패턴 적용
"""
import logging
import json
import uuid
import time
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from webapp.models import QueryRequest
from src.agent.domain import QueryParam
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
    """SQL Agent 스트리밍 API - 멀티턴 대화 지원"""
    
    async def generate_stream():
        # 세션 관리 개선: session_id를 thread_id로 사용
        session_id = request.session_id or str(uuid.uuid4())
        thread_id = request.thread_id or session_id  # thread_id가 없으면 session_id 사용
        
        try:
            logger.info(f"SQL Agent 요청: {request.question[:50]}...")
            logger.info(f"세션 정보 - session_id: {session_id}, thread_id: {thread_id}")
            
            # 직접 생성 방식으로 Agent 서비스 가져오기
            logger.info("Agent 서비스 인스턴스 가져오기 시작")
            agent_service = await get_sql_agent_service()
            logger.info("Agent 서비스 인스턴스 가져오기 완료")
            
            # QueryParam 도메인 객체 생성
            query_param = QueryParam.from_request(
                question=request.question,
                session_id=thread_id,
                model=getattr(request, 'model', 'gemini-2.5-flash-lite')
            )
            
            # 멀티턴 대화를 위한 스트리밍 처리
            logger.info("에이전트 서비스 스트리밍 시작")
            chunk_count = 0
            async for chunk in agent_service.process_query_stream(
                question=request.question,
                query_param=query_param
            ):
                chunk_count += 1
                
                # JSON 문자열을 딕셔너리로 파싱
                try:
                    if isinstance(chunk, str):
                        chunk_data = json.loads(chunk.strip())
                    else:
                        chunk_data = chunk
                    
                    logger.info(f"스트림 청크 #{chunk_count} 수신: {chunk_data.get('type', 'unknown')}")
                    
                    # 클라이언트에게 세션 정보 전달
                    if chunk_data.get("type") == "start":
                        chunk_data["session_id"] = session_id
                        chunk_data["thread_id"] = thread_id
                    
                    yield f"data: {safe_json_dumps(chunk_data)}\n\n"
                    
                except json.JSONDecodeError:
                    logger.warning(f"JSON 파싱 실패: {chunk}")
                    yield f"data: {chunk}\n\n"
            
        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            error_chunk = {
                "type": "error",
                "content": f"처리 중 오류가 발생했습니다: {str(e)}",
                "session_id": session_id,
                "thread_id": thread_id,
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
    """Agent 상태 확인 - 직접 생성 방식 적용"""
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

