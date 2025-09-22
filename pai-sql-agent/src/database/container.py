"""
Database DI Container - Infrastructure Layer
세션 팩토리 및 데이터베이스 연결 관리
"""
import logging
from dependency_injector import containers, providers

from .settings import get_database_settings
from .session_factory import DatabaseSessionFactory

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    """데이터베이스 Infrastructure Layer 컨테이너 - 순환참조 제거"""
    
    # 1. 설정 주입 (싱글톤)
    settings = providers.Singleton(get_database_settings)
    
    # 2. 세션 팩토리 인스턴스 (리소스로 생명주기 관리)
    session_factory_instance = providers.Resource(
        DatabaseSessionFactory,
        settings=settings
    )
    
    # 3. 세션 팩토리 함수 (호출 가능한 컨텍스트 매니저)
    session_factory = providers.Callable(
        lambda factory_instance: factory_instance.get_session,
        factory_instance=session_factory_instance
    )


# ===== 파일 끝 =====
# DatabaseContainer는 직접 사용하지 않고, 싱글톤 서비스 패턴 사용
# get_database_service()를 통해 직접 접근
