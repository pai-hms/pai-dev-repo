"""
Application Container - Clean Architecture 최상위 조합자
계층적 의존성 주입을 통한 전체 시스템 구성
"""
import logging
from dependency_injector import containers, providers
from src.agent.container import AgentContainer
from src.llm.container import LLMContainer
from src.database.container import DatabaseContainer

logger = logging.getLogger(__name__)


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Clean Architecture - Application Container (최상위 조합자)
    
    레이어 구조:
    1. Infrastructure Layer: Database, LLM
    2. Application Layer: Agent (비즈니스 로직)
    3. Presentation Layer: FastAPI (webapp/routers)
    
    의존성 방향: 상위 → 하위 (단방향)
    """
    
    # Configuration Layer
    config = providers.Configuration()
    
    # Infrastructure Layer (기반 인프라)
    database = providers.Container(DatabaseContainer)  # 데이터 저장소
    llm = providers.Container(LLMContainer)            # LLM 모델 관리
    
    # Application Layer (비즈니스 로직) - Infrastructure에 의존
    agent = providers.Container(
        AgentContainer,
        llm_container=llm  # Infrastructure Layer 의존성 주입
        # Database는 tools에서 직접 런타임 접근
    )


# 전역 애플리케이션 컨테이너
_app_container = None


async def get_app_container() -> ApplicationContainer:
    """애플리케이션 컨테이너 싱글톤 인스턴스 반환 (비동기 초기화)"""
    global _app_container
    
    if _app_container is None:
        _app_container = ApplicationContainer()
        
        # 리소스 초기화 (Database 등)
        try:
            await _app_container.init_resources()
            logger.info("Application DI 컨테이너 생성 및 초기화 완료")
        except Exception as e:
            logger.error(f"Application 컨테이너 초기화 실패: {e}")
            _app_container = None
            raise
    
    return _app_container


async def close_app_container():
    """애플리케이션 컨테이너 정리"""
    global _app_container
    
    if _app_container is not None:
        try:
            # dependency-injector의 shutdown_resources 메서드 확인
            if hasattr(_app_container, 'shutdown_resources'):
                shutdown_method = getattr(_app_container, 'shutdown_resources')
                
                # 메서드 호출
                shutdown_result = shutdown_method()
                
                # 결과가 None이 아니고 awaitable인 경우에만 await
                if shutdown_result is not None and hasattr(shutdown_result, '__await__'):
                    await shutdown_result
                    logger.info("Application 컨테이너 비동기 리소스 정리 완료")
                else:
                    logger.info("Application 컨테이너 동기 리소스 정리 완료")
            else:
                logger.info("Application 컨테이너에 shutdown_resources 메서드 없음 - 수동 정리")
            
        except Exception as e:
            logger.warning(f"Application 컨테이너 정리 중 오류 (무시): {e}")
            # 오류가 발생해도 계속 진행
        
        _app_container = None
        logger.info("Application DI 컨테이너 정리 완료")
