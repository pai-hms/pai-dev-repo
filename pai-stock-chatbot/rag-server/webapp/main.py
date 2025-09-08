# rag-server/webapp/main.py
import sys
import os
import logging
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

# rag-server를 Python 경로에 추가
rag_server_root = Path(__file__).parent.parent
sys.path.insert(0, str(rag_server_root))

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from webapp.routers import chat
from webapp.container import create_container  #컨테이너 추가
from src.exceptions import (
    AuthorizationException,
    ClientException,
    PermissionDeniedException,
    RagStackException,
    ServerException,
)

logger = logging.getLogger(__name__)

def _setup_lifespan(container):
    """애플리케이션 생명주기 설정"""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Setting up Stock Chatbot application")
        app.container = container
        yield
        logger.info("Tearing down Stock Chatbot application")
    return lifespan

def _create_fastapi_app(lifespan_manager) -> FastAPI:
    """FastAPI 앱 인스턴스 생성"""
    return FastAPI(
        title="Stock Agent API",
        description="A streaming chatbot for stock prices using LangGraph and FastAPI.",
        version="1.0.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        servers=[
            {"url": "http://localhost:8000", "description": "Local Development"},
            {"url": "https://api.stockchatbot.com", "description": "Production"},
        ],
        lifespan=lifespan_manager,
        generate_unique_id_function=lambda route: route.name,
    )

def _setup_container_and_wiring():
    """DI 컨테이너 설정 및 와이어링"""
    container = create_container()
    container.wire(modules=["webapp.dependency", "webapp.routers.chat"])
    return container

def create_app() -> FastAPI:
    """애플리케이션 생성 및 설정"""
    # 컨테이너 설정
    container = _setup_container_and_wiring()
    
    # 생명주기 관리자 설정
    lifespan_manager = _setup_lifespan(container)
    
    # FastAPI 앱 생성
    app = _create_fastapi_app(lifespan_manager)
    app.container = container

    # 라우터 등록
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

    # 미들웨어
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_trace_id():
        """trace ID 생성"""
        return str(uuid.uuid4())[:8]

    # 예외 처리기들 (원본 구조 그대로)
    @app.exception_handler(ClientException)
    async def client_exception_handler(request: Request, exc: ClientException):
        logger.warning(f"Client exception: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "message": exc.message,
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(AuthorizationException)
    async def authorization_exception_handler(
        request: Request, exc: AuthorizationException
    ):
        logger.warning(f"Authorization exception: {exc.message}")
        return JSONResponse(
            status_code=401,
            content={
                "message": exc.message,
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(PermissionDeniedException)
    async def permission_denied_exception_handler(
        request: Request, exc: PermissionDeniedException
    ):
        logger.warning(f"Permission denied exception: {exc.message}")
        return JSONResponse(
            status_code=403,
            content={
                "message": exc.message,
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(ServerException)
    async def server_exception_handler(request: Request, exc: ServerException):
        logger.error(f"Server exception: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "message": exc.message,
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(RagStackException)
    async def ragstack_exception_handler(request: Request, exc: RagStackException):
        logger.error(f"RagStack exception: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "message": exc.message,
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error occurred",
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "message": exc.errors(),
                "code": exc.__class__.__name__,
                "trace_id": get_trace_id(),
            },
        )

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Stock Agent API"}

    return app

# FastAPI 앱 인스턴스
app = create_app()