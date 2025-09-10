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
        used_tools_data = result.get("used_tools", [])
        
        # 마지막 AI 메시지 찾기
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                final_message = str(msg.content)
                break
        
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
            success=True,
            message=final_message or "쿼리가 성공적으로 처리되었습니다.",
            sql_queries=sql_queries,
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
async def stream_sql_agent(request: QueryRequest):
    """SQL Agent에 질문을 보내고 스트리밍 응답을 받습니다 (LLM 토큰별)"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # 세션 ID 생성 (없는 경우)
            session_id = request.session_id or str(uuid.uuid4())
            
            # 에이전트 서비스 가져오기
            agent_service = get_sql_agent_service(enable_checkpointer=True)
            
            # LLM 토큰별 + 도구 실행 상태 스트리밍
            final_state_info = None
            
            async for chunk in agent_service.stream_query(request.question, session_id):
                if chunk.get("type") == "token":
                    # LLM 토큰을 바로 전달
                    token_chunk = StreamChunk(
                        type="token",
                        content=chunk["content"]
                    )
                    yield f"data: {token_chunk.model_dump_json()}\n\n"
                elif chunk.get("type") == "final_state":
                    # 최종 상태 정보 저장 (나중에 사용)
                    final_state_info = chunk["content"]
                elif chunk.get("type") == "error":
                    # 에러 처리
                    error_chunk = StreamChunk(
                        type="error",
                        content=chunk["content"]
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                    return
            
            # 최종 상태 정보 전달 (도구 정보 포함)
            if final_state_info:
                # 사용된 도구들을 개별적으로 스트리밍
                used_tools = final_state_info.get("used_tools", [])
                for tool in used_tools:
                    tool_chunk = StreamChunk(
                        type="tool_execution",
                        content=json.dumps({
                            "tool_name": tool.get("tool_function", "Unknown"),
                            "description": tool.get("tool_description", ""),
                            "arguments": tool.get("arguments", {}),
                            "status": "completed" if tool.get("success") else "failed"
                        })
                    )
                    yield f"data: {tool_chunk.model_dump_json()}\n\n"
                
                # 최종 상태 정보도 전달
                state_chunk = StreamChunk(
                    type="final_state",
                    content=json.dumps(final_state_info)
                )
                yield f"data: {state_chunk.model_dump_json()}\n\n"
            
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


@router.get("/test-memory")
async def test_memory_functionality():
    """메모리 기능 테스트 엔드포인트"""
    try:
        # 체크포인터 활성화된 서비스 생성
        agent_service = get_sql_agent_service(enable_checkpointer=True)
        test_session = f"test_{int(time.time())}"
        
        # 첫 번째 질문
        result1 = await agent_service.invoke_query(
            "안녕하세요! 저는 홍민식입니다.", 
            session_id=test_session
        )
        
        if result1.get('error_message'):
            return {
                "success": False,
                "error": result1['error_message'],
                "test_session": test_session
            }
        
        # 두 번째 질문 (메모리 테스트)
        result2 = await agent_service.invoke_query(
            "제 이름이 뭐라고 했죠?", 
            session_id=test_session
        )
        
        if result2.get('error_message'):
            return {
                "success": False,
                "error": result2['error_message'],
                "test_session": test_session
            }
        
        # 응답에서 이름이 포함되어 있는지 확인
        messages2 = result2.get('messages', [])
        answer = ""
        if messages2:
            for msg in reversed(messages2):
                if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                    answer = str(msg.content)
                    break
        
        memory_working = any(name in answer for name in ["홍민식", "민식", "홍"])
        
        return {
            "success": True,
            "memory_working": memory_working,
            "test_session": test_session,
            "first_response_messages": len(result1.get('messages', [])),
            "second_response_messages": len(result2.get('messages', [])),
            "second_response": answer[:200] if answer else "응답 없음",
            "search_terms": ["홍민식", "민식", "홍"]
        }
        
    except Exception as e:
        logger.error(f"메모리 테스트 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
