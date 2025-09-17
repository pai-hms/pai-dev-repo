import time
import json
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage

from webapp.models import QueryRequest, QueryResponse, StreamChunk, ToolInfo
from src.agent.service import get_sql_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/query", response_model=QueryResponse)
async def query_sql_agent(request: QueryRequest) -> QueryResponse:
    """SQL Agent에 질문을 보내고 응답을 받습니다"""
    start_time = time.time()
    
    try:
        # 세션 ID 생성 (없는 경우)
        session_id = request.session_id or str(uuid.uuid4())
        
        # 새로운 SQL Agent 서비스 가져오기
        agent_service = await get_sql_agent_service()
        
        # 쿼리 실행
        result = await agent_service.query(request.question, session_id)
        
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
        
        # 새로운 응답 형식 처리
        final_message = result.get("message", "")
        sql_queries = result.get("sql_queries", [])
        used_tools_data = result.get("used_tools", [])
        
        # 새로운 형식에서는 final_message가 이미 준비됨
        results = result.get("results", [])
        
        # 도구 정보를 ToolInfo 모델로 변환
        used_tools = []
        for tool_data in used_tools_data:
            tool_info = ToolInfo(
                tool_name=tool_data.get("tool_name", ""),
                tool_function=tool_data.get("tool_function", ""),
                tool_description=tool_data.get("tool_description", ""),
                arguments=tool_data.get("arguments", {}),
                execution_order=tool_data.get("execution_order", 0),
                success=tool_data.get("success", False),
                result_preview=tool_data.get("result_preview"),
                error_message=tool_data.get("error_message")
            )
            used_tools.append(tool_info)
        
        return QueryResponse(
            success=result.get("success", True),
            message=final_message or "쿼리가 성공적으로 처리되었습니다.",
            sql_queries=sql_queries,
            results=results,
            used_tools=used_tools,
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
async def query_sql_agent_stream(request: QueryRequest) -> StreamingResponse:
    """SQL Agent에 질문을 보내고 스트리밍 응답을 받습니다"""
    
    async def generate_stream():
        try:
            # 세션 ID 생성 (없는 경우)
            session_id = request.session_id or str(uuid.uuid4())
            
            # 새로운 SQL Agent 서비스 가져오기
            agent_service = await get_sql_agent_service()
            
            # 쿼리 실행
            result = await agent_service.query(request.question, session_id)
            
            if result.get("error_message"):
                yield f"data: {json.dumps({'type': 'error', 'content': result['error_message']})}\n\n"
                return
            
            # 응답 메시지를 단어별로 스트리밍
            final_message = result.get("message", "")
            used_tools = result.get("used_tools", [])
            
            # 도구 실행 정보 전송
            for tool in used_tools:
                tool_chunk = StreamChunk(
                    type="tool_execution",
                    content=tool
                )
                yield f"data: {tool_chunk.model_dump_json()}\n\n"
            
            # 메시지를 단어별로 전송
            words = final_message.split()
            for word in words:
                token_chunk = StreamChunk(
                    type="token", 
                    content=word + " "
                )
                yield f"data: {token_chunk.model_dump_json()}\n\n"
            
            # 최종 상태 전송
            final_chunk = StreamChunk(
                type="final_state",
                content={
                    "used_tools": used_tools,
                    "message": final_message,
                    "session_id": session_id,
                    "success": result.get("success", True)
                }
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            
        except Exception as e:
            logger.error(f"스트리밍 처리 중 오류: {str(e)}")
            error_chunk = StreamChunk(
                type="error",
                content=str(e)
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


# 통합 에이전트 제거 - 단일 에이전트만 사용