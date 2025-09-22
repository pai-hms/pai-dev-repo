import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from webapp.routers import agent, data
from webapp.models import ErrorResponse
from webapp.container import get_app_container, close_app_container
from src.agent.settings import get_settings
from src.database.service import get_database_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리 - 완전한 DI 기반"""
    # 시작 시
    logger.info("애플리케이션 시작 (DI 기반)")
    
    try:
        # DI 컨테이너 초기화 (비동기)
        app_container = await get_app_container()
        logger.info("DI 컨테이너 초기화 완료")
        
        # 데이터베이스 테이블 생성 (DI 기반)
        try:
            db_service = await get_database_service()
            # 데이터베이스 연결 테스트
            test_result = await db_service.execute_custom_query("SELECT 1 as test")
            if test_result.success:
                logger.info("데이터베이스 연결 확인 완료")
            else:
                logger.warning("데이터베이스 연결 테스트 실패")
        except Exception as e:
            logger.warning(f"데이터베이스 초기화 중 오류: {e}")
        
        # 애플리케이션에 컨테이너 바인딩
        app.container = app_container
        
        yield
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 실패: {e}")
        raise
    finally:
        # 종료 시
        logger.info("애플리케이션 종료 시작")
        try:
            await close_app_container()
            logger.info("DI 컨테이너 정리 완료")
        except Exception as e:
            logger.error(f"DI 컨테이너 정리 실패: {e}")
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
    """헬스 체크 엔드포인트 - DI 기반"""
    try:
        # 데이터베이스 연결 테스트 (DI 기반)
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