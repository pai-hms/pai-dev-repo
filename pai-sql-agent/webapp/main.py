import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from webapp.routers import agent, data
from webapp.models import ErrorResponse
from src.config.settings import get_settings
from src.database.connection import get_database_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("애플리케이션 시작")
    
    try:
        # 데이터베이스 연결 테스트
        db_manager = get_database_manager()
        logger.info("데이터베이스 연결 완료")
        
        yield
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 중 오류: {str(e)}")
        raise
    finally:
        # 종료 시
        logger.info("애플리케이션 종료")
        try:
            db_manager = get_database_manager()
            await db_manager.close()
        except:
            pass


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="PAI SQL Agent",
    description="LangGraph 기반 한국 센서스 통계 SQL 에이전트",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(agent.router)
app.include_router(data.router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "PAI SQL Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            error_message=exc.detail
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.error(f"처리되지 않은 예외: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            error_message="내부 서버 오류가 발생했습니다"
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "webapp.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
