import time
import json
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage

from webapp.models import QueryRequest, QueryResponse, StreamChunk
from src.agent.graph import get_sql_agent_graph, create_session_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/query", response_model=QueryResponse)
async def query_sql_agent(request: QueryRequest) -> QueryResponse:
    """SQL Agent에 질문을 보내고 응답을 받습니다"""
    start_time = time.time()
    
    try:
        # 세션 ID 생성 (없는 경우)
        session_id = request.session_id or str(uuid.uuid4())
        
        # 에이전트 그래프 가져오기
        agent_graph = get_sql_agent_graph()
        
        # 세션 설정 생성
        config = await create_session_config(session_id)
        
        # 쿼리 실행
        result = await agent_graph.invoke_query(request.question, config)
        
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
    """SQL Agent에 질문을 보내고 스트리밍 응답을 받습니다"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # 세션 ID 생성 (없는 경우)
            session_id = request.session_id or str(uuid.uuid4())
            
            # 에이전트 그래프 가져오기
            agent_graph = get_sql_agent_graph()
            
            # 세션 설정 생성
            config = await create_session_config(session_id)
            
            # 시작 메시지
            start_chunk = StreamChunk(
                type="message",
                content="질문을 분석하고 있습니다..."
            )
            yield f"data: {start_chunk.model_dump_json()}\n\n"
            
            # 스트리밍 실행
            async for chunk in agent_graph.stream_query(request.question, config):
                # 각 노드 실행 결과를 스트리밍
                for node_name, node_result in chunk.items():
                    if node_name == "generate_response":
                        # 최종 응답인 경우
                        messages = node_result.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, 'content'):
                                response_chunk = StreamChunk(
                                    type="message",
                                    content=str(last_msg.content)
                                )
                                yield f"data: {response_chunk.model_dump_json()}\n\n"
                    
                    elif node_name == "execute_tools":
                        # 도구 실행 결과인 경우
                        sql_results = node_result.get("sql_results", [])
                        if sql_results:
                            for sql_result in sql_results:
                                sql_chunk = StreamChunk(
                                    type="sql_result",
                                    content=sql_result
                                )
                                yield f"data: {sql_chunk.model_dump_json()}\n\n"
                    
                    # 에러 처리
                    if node_result.get("error_message"):
                        error_chunk = StreamChunk(
                            type="error",
                            content=node_result["error_message"]
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
