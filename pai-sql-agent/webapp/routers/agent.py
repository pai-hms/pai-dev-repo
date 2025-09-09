import time
import json
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage

from webapp.models import QueryRequest, QueryResponse, StreamChunk
from src.agent.graph import get_sql_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/query", response_model=QueryResponse)
async def query_sql_agent(request: QueryRequest) -> QueryResponse:
    """SQL Agent에 질문을 보내고 응답을 받습니다"""
    start_time = time.time()
    
    try:
        # 세션 ID 생성 (없는 경우)
        session_id = request.session_id or str(uuid.uuid4())
        
        # 에이전트 서비스 가져오기
        agent_service = get_sql_agent_service(enable_checkpointer=True)
        
        # 쿼리 실행
        result = await agent_service.invoke_query(request.question, session_id)
        
        # 결과 파싱
        processing_time = time.time() - start_time
        
        if result.get("error_message"):
            return QueryResponse(
                success=False,
                message="쿼리 처리 중 오류가 발생했습니다.",
                error_message=result["error_message"],
                session_id=session_id,
                processing_time=processing_time
            )
        
        # 메시지에서 응답과 SQL 결과 추출
        messages = result.get("messages", [])
        final_message = ""
        sql_queries = result.get("sql_results", [])
        
        # 마지막 AI 메시지 찾기
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                final_message = str(msg.content)
                break
        
        return QueryResponse(
            success=True,
            message=final_message or "쿼리가 성공적으로 처리되었습니다.",
            sql_queries=sql_queries,
            session_id=session_id,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"SQL Agent 쿼리 처리 중 오류: {str(e)}")
        processing_time = time.time() - start_time
        
        return QueryResponse(
            success=False,
            message="내부 서버 오류가 발생했습니다.",
            error_message=str(e),
            session_id=request.session_id or str(uuid.uuid4()),
            processing_time=processing_time
        )


@router.post("/query/stream")
async def stream_sql_agent(request: QueryRequest):
    """SQL Agent에 질문을 보내고 스트리밍 응답을 받습니다 (LLM 토큰별)"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # 세션 ID 생성 (없는 경우)
            session_id = request.session_id or str(uuid.uuid4())
            
            # 에이전트 서비스 가져오기
            agent_service = get_sql_agent_service(enable_checkpointer=True)
            
            # LLM 토큰별 스트리밍 실행
            async for chunk in agent_service.stream_query(request.question, session_id):
                if chunk.get("type") == "token":
                    # LLM 토큰을 바로 전달
                    token_chunk = StreamChunk(
                        type="token",
                        content=chunk["content"]
                    )
                    yield f"data: {token_chunk.model_dump_json()}\n\n"
                elif chunk.get("type") == "error":
                    # 에러 처리
                    error_chunk = StreamChunk(
                        type="error",
                        content=chunk["content"]
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                    return
            
            # 완료 메시지
            complete_chunk = StreamChunk(
                type="complete",
                content="처리가 완료되었습니다."
            )
            yield f"data: {complete_chunk.model_dump_json()}\n\n"
            
        except Exception as e:
            logger.error(f"스트리밍 처리 중 오류: {str(e)}")
            error_chunk = StreamChunk(
                type="error",
                content=f"오류가 발생했습니다: {str(e)}"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )