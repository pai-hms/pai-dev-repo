"""Agent API routes with JSON streaming support."""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from webapp.models import QuestionRequest, AgentResponse, StreamChunk
from webapp.dependencies import get_agent_service
from src.agent.graph import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/ask", response_model=AgentResponse)
async def ask_question(
    request: QuestionRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Ask a question to the SQL agent."""
    try:
        result = await agent_service.ask_question(
            question=request.question,
            thread_id=request.thread_id,
        )
        
        if result["success"]:
            data = result["data"]
            return AgentResponse(
                success=True,
                response=data.get("response"),
                thread_id=data.get("thread_id"),
                iteration_count=data.get("iteration_count"),
                sql_query=data.get("sql_query"),
                query_result=data.get("query_result"),
            )
        else:
            return AgentResponse(
                success=False,
                error=result["error"],
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_question(
    request: QuestionRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    """Stream agent response with Server-Sent Events."""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response following linear principle."""
        try:
            # Send initial chunk
            initial_chunk = StreamChunk(
                type="start",
                content={
                    "message": "Starting analysis...",
                    "thread_id": request.thread_id or str(uuid.uuid4()),
                }
            )
            yield f"data: {initial_chunk.json()}\n\n"
            
            # Stream agent execution
            async for chunk in agent_service.stream_question(
                question=request.question,
                thread_id=request.thread_id,
            ):
                if chunk["success"]:
                    # Process different types of chunks
                    chunk_data = chunk["data"]
                    
                    # Determine chunk type based on content
                    if isinstance(chunk_data, dict):
                        # Check if it's a node execution
                        if "agent" in chunk_data:
                            stream_chunk = StreamChunk(
                                type="agent",
                                content={
                                    "node": "agent",
                                    "data": chunk_data["agent"],
                                }
                            )
                        elif "tools" in chunk_data:
                            stream_chunk = StreamChunk(
                                type="tool",
                                content={
                                    "node": "tools", 
                                    "data": chunk_data["tools"],
                                }
                            )
                        else:
                            stream_chunk = StreamChunk(
                                type="update",
                                content=chunk_data,
                            )
                        
                        yield f"data: {stream_chunk.json()}\n\n"
                else:
                    # Error chunk
                    error_chunk = StreamChunk(
                        type="error",
                        content={"error": chunk["error"]},
                    )
                    yield f"data: {error_chunk.json()}\n\n"
            
            # Send final chunk
            final_chunk = StreamChunk(
                type="final",
                content={"message": "Analysis complete"},
            )
            yield f"data: {final_chunk.json()}\n\n"
            
        except Exception as e:
            error_chunk = StreamChunk(
                type="error",
                content={"error": str(e)},
            )
            yield f"data: {error_chunk.json()}\n\n"
    
    return EventSourceResponse(generate_stream())


@router.post("/stream-json")
async def stream_question_json(
    request: QuestionRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    """Stream agent response as JSON lines for faster first token."""
    
    async def generate_json_stream() -> AsyncGenerator[bytes, None]:
        """Generate JSON streaming response for fast first token."""
        try:
            # Send immediate first token
            first_token = {
                "type": "start",
                "content": {
                    "message": "🔍 Analyzing your question...",
                    "thread_id": request.thread_id or str(uuid.uuid4()),
                    "question": request.question,
                },
                "timestamp": StreamChunk().timestamp.isoformat(),
            }
            yield (json.dumps(first_token) + "\n").encode()
            
            # Stream agent execution with detailed progress
            step_count = 0
            async for chunk in agent_service.stream_question(
                question=request.question,
                thread_id=request.thread_id,
            ):
                step_count += 1
                
                if chunk["success"]:
                    chunk_data = chunk["data"]
                    
                    # Enhanced chunk processing for better UX
                    if isinstance(chunk_data, dict):
                        # Agent reasoning step
                        if "agent" in chunk_data:
                            agent_data = chunk_data["agent"]
                            if "messages" in agent_data:
                                messages = agent_data["messages"]
                                if messages:
                                    last_message = messages[-1]
                                    
                                    # Check if it's a tool call
                                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                                        for tool_call in last_message.tool_calls:
                                            tool_chunk = {
                                                "type": "tool_call",
                                                "content": {
                                                    "step": step_count,
                                                    "tool_name": tool_call["name"],
                                                    "tool_args": tool_call["args"],
                                                    "message": f"🔧 Executing {tool_call['name']}...",
                                                },
                                                "timestamp": StreamChunk().timestamp.isoformat(),
                                            }
                                            yield (json.dumps(tool_chunk) + "\n").encode()
                                    else:
                                        # Regular agent response
                                        response_chunk = {
                                            "type": "agent_response",
                                            "content": {
                                                "step": step_count,
                                                "response": last_message.content,
                                                "message": "💭 Agent thinking...",
                                            },
                                            "timestamp": StreamChunk().timestamp.isoformat(),
                                        }
                                        yield (json.dumps(response_chunk) + "\n").encode()
                        
                        # Tool execution result
                        elif "tools" in chunk_data:
                            tool_result = {
                                "type": "tool_result",
                                "content": {
                                    "step": step_count,
                                    "result": chunk_data["tools"],
                                    "message": "✅ Tool execution completed",
                                },
                                "timestamp": StreamChunk().timestamp.isoformat(),
                            }
                            yield (json.dumps(tool_result) + "\n").encode()
                        
                        # General update
                        else:
                            update_chunk = {
                                "type": "update",
                                "content": {
                                    "step": step_count,
                                    "data": chunk_data,
                                },
                                "timestamp": StreamChunk().timestamp.isoformat(),
                            }
                            yield (json.dumps(update_chunk) + "\n").encode()
                else:
                    # Error during execution
                    error_chunk = {
                        "type": "error",
                        "content": {
                            "step": step_count,
                            "error": chunk["error"],
                            "message": "❌ Error occurred",
                        },
                        "timestamp": StreamChunk().timestamp.isoformat(),
                    }
                    yield (json.dumps(error_chunk) + "\n").encode()
            
            # Send completion
            final_chunk = {
                "type": "complete",
                "content": {
                    "message": "🎉 Analysis complete!",
                    "total_steps": step_count,
                },
                "timestamp": StreamChunk().timestamp.isoformat(),
            }
            yield (json.dumps(final_chunk) + "\n").encode()
            
        except Exception as e:
            error_chunk = {
                "type": "error",
                "content": {
                    "error": str(e),
                    "message": "❌ Unexpected error occurred",
                },
                "timestamp": StreamChunk().timestamp.isoformat(),
            }
            yield (json.dumps(error_chunk) + "\n").encode()
    
    return StreamingResponse(
        generate_json_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
