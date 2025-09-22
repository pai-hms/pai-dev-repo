import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from webapp.routers import agent, data
from webapp.models import ErrorResponse
from src.agent.settings import get_settings
from src.database.factory import get_database_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리 - Factory 패턴 기반"""
    # 시작 시
    logger.info("애플리케이션 시작 (Factory 패턴 기반)")
    
    try:
        # 데이터베이스 연결 테스트
        try:
            db_service = await get_database_service()
            test_result = await db_service.execute_custom_query("SELECT 1 as test")
            if test_result.success:
                logger.info("데이터베이스 연결 확인 완료")
            else:
                logger.warning("데이터베이스 연결 테스트 실패")
        except Exception as e:
            logger.warning(f"데이터베이스 초기화 중 오류: {e}")
        
        yield
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 실패: {e}")
        raise
    finally:
        # 종료 시
        logger.info("애플리케이션 종료 시작")
        logger.info("애플리케이션 종료 완료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="PAI SQL Agent API",
    description="한국 통계청 데이터 분석용 실시간 스트리밍 SQL Agent",
    version="3.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 특정 도메인만 허용
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
        "message": "PAI SQL Agent API v3.0.0",
        "description": "한국 통계청 데이터 분석용 실시간 스트리밍 SQL Agent",
        "features": [
            "실시간 토큰 스트리밍",
            "LangGraph 통합",
            "SGIS API 연동",
            "멀티턴 대화 지원"
        ],
        "endpoints": {
            "agent": "/api/agent/query",
            "data": "/api/data/database-info",
            "health": "/api/data/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트 - Factory 패턴 기반"""
    try:
        # 데이터베이스 연결 테스트
        db_service = await get_database_service()
        test_result = await db_service.execute_custom_query("SELECT 1 as test")
        db_healthy = test_result.success
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": "3.0.0",
            "timestamp": "2024-12-19"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "version": "3.0.0",
            "timestamp": "2024-12-19"
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error_message=f"HTTP {exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.error(f"예상되지 않은 오류 발생: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message="내부 서버 오류가 발생했습니다",
            error_message=str(exc)
        ).dict()
    )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "webapp.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )