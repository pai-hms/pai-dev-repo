# rag-server/webapp/main.py
from fastapi import FastAPI
import sys
import os

# rag-server 폴더를 Python 경로에 추가
rag_server_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(rag_server_root))

from webapp.routers import chat

app = FastAPI(
    title="Stock Agent API",
    description="A streaming chatbot for stock prices using LangGraph and FastAPI.",
    version="1.0.0"
)

# /api/v1 접두사와 함께 chat 라우터 포함
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Stock Agent API"}