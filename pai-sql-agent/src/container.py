"""
Dependency Injection Container - IoC 패턴 구현
국세청 챗봇 아키텍처를 참고한 계층적 의존성 주입
"""
import logging
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from src.database.connection import get_database_manager
from src.database.service import DatabaseService
from src.llm.service import get_llm_service
from src.agent.service import SQLAgentService
from src.agent.settings import get_agent_settings

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """데이터베이스 관련 의존성 컨테이너"""
    
    # 설정
    config = providers.Configuration()
    
    # 데이터베이스 매니저
    database_manager = providers.Resource(get_database_manager)
    
    # 데이터베이스 서비스
    database_service = providers.Factory(
        DatabaseService,
        db_manager=database_manager
    )


class LLMContainer(containers.DeclarativeContainer):
    """LLM 관련 의존성 컨테이너"""
    
    # 설정
    config = providers.Configuration()
    
    # LLM 서비스
    llm_service = providers.Resource(get_llm_service)


class AgentContainer(containers.DeclarativeContainer):
    """에이전트 관련 의존성 컨테이너"""
    
    # 설정
    config = providers.Configuration()
    
    # 에이전트 설정
    agent_settings = providers.Resource(get_agent_settings)
    
    # SQL 에이전트 서비스 (싱글톤)
    sql_agent_service = providers.Singleton(
        SQLAgentService.get_instance
    )


class ApplicationContainer(containers.DeclarativeContainer):
    """애플리케이션 전체 의존성 컨테이너"""
    
    # 설정
    config = providers.Configuration()
    
    # 하위 컨테이너들
    database = providers.Container(DatabaseContainer)
    llm = providers.Container(LLMContainer)
    agent = providers.Container(AgentContainer)
    
    # 로깅 설정
    logging_config = providers.Configuration()


# 전역 컨테이너 인스턴스
container = ApplicationContainer()


async def initialize_container():
    """컨테이너 초기화"""
    try:
        logger.info("DI 컨테이너 초기화 시작")
        
        # 설정 로드
        container.config.from_dict({
            "logging": {"level": "INFO"},
            "database": {"pool_size": 20},
            "llm": {"model": "gpt-4"},
            "agent": {"max_iterations": 10}
        })
        
        # 리소스 초기화
        await container.database.database_manager()
        await container.llm.llm_service()
        await container.agent.agent_settings()
        
        logger.info("DI 컨테이너 초기화 완료")
        
    except Exception as e:
        logger.error(f"DI 컨테이너 초기화 실패: {e}")
        raise


async def cleanup_container():
    """컨테이너 정리"""
    try:
        logger.info("🧹 DI 컨테이너 정리 시작")
        
        # 리소스 정리
        await container.database.database_manager.shutdown()
        await container.llm.llm_service.shutdown()
        
        logger.info("DI 컨테이너 정리 완료")
        
    except Exception as e:
        logger.warning(f"DI 컨테이너 정리 중 오류: {e}")


# 의존성 주입 데코레이터들
def inject_database_service():
    """데이터베이스 서비스 주입"""
    return inject(Provide[ApplicationContainer.database.database_service])


def inject_llm_service():
    """LLM 서비스 주입"""
    return inject(Provide[ApplicationContainer.llm.llm_service])


def inject_agent_service():
    """에이전트 서비스 주입"""
    return inject(Provide[ApplicationContainer.agent.sql_agent_service])


# 컨테이너 접근 헬퍼 함수들
async def get_database_service_from_container():
    """컨테이너에서 데이터베이스 서비스 반환"""
    return await container.database.database_service()


async def get_llm_service_from_container():
    """컨테이너에서 LLM 서비스 반환"""
    return await container.llm.llm_service()


async def get_agent_service_from_container():
    """컨테이너에서 에이전트 서비스 반환"""
    return await container.agent.sql_agent_service()
