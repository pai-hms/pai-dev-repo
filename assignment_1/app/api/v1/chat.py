# app/api/v1/chat.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
# Import the executor instance directly from graph.py
from ...agents.graph import agent_executor 

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: str 

# The generator no longer needs the 'agent' parameter passed to it
async def stream_generator(message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    # Use the globally imported agent_executor
    async for event in agent_executor.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        version="v1"
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield content

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        # Pass the arguments directly to the generator
        stream_generator(request.message, request.thread_id),
        media_type="text/event-stream"
    )