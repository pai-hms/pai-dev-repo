"""
SQL Agent 설정 관리
"""
from dataclasses import dataclass
from src.config.settings import get_settings


@dataclass
class AgentConfig:
    """Agent 설정"""
    
    # LLM 설정
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # 워크플로우 설정
    max_iterations: int = 3
    timeout_seconds: int = 30
    
    # SQL 설정
    max_result_rows: int = 50
    query_timeout: int = 10


_agent_config: AgentConfig = None


def get_agent_config() -> AgentConfig:
    """Agent 설정 싱글톤 인스턴스"""
    global _agent_config
    
    if _agent_config is None:
        settings = get_settings()
        _agent_config = AgentConfig(
            model_name="gpt-4o-mini",  # 기본값 사용
            temperature=0.1,
            max_tokens=2000
        )
    
    return _agent_config