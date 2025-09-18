"""
Tool Agent의 비즈니스 로직을 담당하는 서비스
도메인 로직과 데이터 접근을 분리
"""
import logging
from typing import Dict, List, Optional, Any
from src.tools.domains import ToolAgent, ToolAgentType
from src.tools.repository import ToolAgentRepository
from src.tools.sql_agent.container import SQLAgentContainer

logger = logging.getLogger(__name__)


class ToolAgentService:
    """Tool Agent 관리 서비스 - SQL Agent 포함"""
    
    def __init__(
        self, 
        repository: ToolAgentRepository,
        sql_agent: SQLAgentContainer,
    ):
        self.repository = repository
        self.sql_agent = sql_agent
    
    async def find_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """특정 챗봇에 연결된 Tool Agent 조회"""
        return await self.repository.find_by_chatbot_id(chatbot_id)
    
    async def find_active_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """특정 챗봇에 연결된 활성 Tool Agent만 조회"""
        return await self.repository.find_active_by_chatbot_id(chatbot_id)
    
    async def create_tool_agent(
        self, 
        chatbot_id: int, 
        agent_type: ToolAgentType,
        config: Dict[str, Any]
    ) -> ToolAgent:
        """새로운 Tool Agent 생성"""
        tool_agent = ToolAgent(
            chatbot_id=chatbot_id,
            agent_type=agent_type,
            config=config,
            is_active=True
        )
        return await self.repository.create(tool_agent)
    
    async def update_tool_agent(
        self, 
        tool_agent_id: int, 
        config: Dict[str, Any]
    ) -> Optional[ToolAgent]:
        """Tool Agent 설정 업데이트"""
        tool_agent = await self.repository.find_by_id(tool_agent_id)
        if not tool_agent:
            return None
        
        tool_agent.config = config
        return await self.repository.update(tool_agent)
    
    async def activate_tool_agent(self, tool_agent_id: int) -> bool:
        """Tool Agent 활성화"""
        tool_agent = await self.repository.find_by_id(tool_agent_id)
        if not tool_agent:
            return False
        
        tool_agent.is_active = True
        await self.repository.update(tool_agent)
        return True
    
    async def deactivate_tool_agent(self, tool_agent_id: int) -> bool:
        """Tool Agent 비활성화"""
        tool_agent = await self.repository.find_by_id(tool_agent_id)
        if not tool_agent:
            return False
        
        tool_agent.is_active = False
        await self.repository.update(tool_agent)
        return True
    
    async def delete_tool_agent(self, tool_agent_id: int) -> bool:
        """Tool Agent 삭제"""
        return await self.repository.delete(tool_agent_id)
    
    # SQL Agent 관련 메서드들
    async def execute_sql_query(
        self, 
        chatbot_id: int, 
        query: str
    ) -> Dict[str, Any]:
        """SQL 쿼리 실행 (SQL Agent 활용)"""
        try:
            # SQL Agent가 활성화되어 있는지 확인
            sql_agents = await self.find_active_by_chatbot_id(chatbot_id)
            sql_agent = next(
                (agent for agent in sql_agents if agent.agent_type == ToolAgentType.SQL_AGENT), 
                None
            )
            
            if not sql_agent:
                return {
                    "success": False,
                    "error": "SQL Agent가 활성화되어 있지 않습니다"
                }
            
            # SQL Agent 컨테이너를 통해 쿼리 실행
            sql_service = await self.sql_agent.get_sql_agent_service()
            result = await sql_service.execute_query(query)
            
            return {
                "success": True,
                "result": result,
                "agent_id": sql_agent.id
            }
            
        except Exception as e:
            logger.error(f"SQL 쿼리 실행 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_sql_agent_status(self, chatbot_id: int) -> Dict[str, Any]:
        """SQL Agent 상태 조회"""
        try:
            sql_agents = await self.find_active_by_chatbot_id(chatbot_id)
            sql_agent = next(
                (agent for agent in sql_agents if agent.agent_type == ToolAgentType.SQL_AGENT), 
                None
            )
            
            if not sql_agent:
                return {
                    "active": False,
                    "message": "SQL Agent가 설정되어 있지 않습니다"
                }
            
            return {
                "active": True,
                "agent_id": sql_agent.id,
                "config": sql_agent.config,
                "created_at": sql_agent.created_at,
                "updated_at": sql_agent.updated_at
            }
            
        except Exception as e:
            logger.error(f"SQL Agent 상태 조회 오류: {e}")
            return {
                "active": False,
                "error": str(e)
            }
    
    async def setup_default_sql_agent(self, chatbot_id: int) -> ToolAgent:
        """기본 SQL Agent 설정"""
        default_config = {
            "database_url": "postgresql://localhost:5432/statistics",
            "max_query_time": 30,
            "allowed_tables": [
                "population_stats",
                "household_stats", 
                "company_stats",
                "house_stats"
            ],
            "enable_cache": True,
            "cache_ttl": 300
        }
        
        return await self.create_tool_agent(
            chatbot_id=chatbot_id,
            agent_type=ToolAgentType.SQL_AGENT,
            config=default_config
        )
    
    async def get_available_tools(self, chatbot_id: int) -> List[Dict[str, Any]]:
        """사용 가능한 도구 목록 조회"""
        active_agents = await self.find_active_by_chatbot_id(chatbot_id)
        
        tools = []
        for agent in active_agents:
            tool_info = {
                "id": agent.id,
                "type": agent.agent_type.value,
                "name": self._get_tool_name(agent.agent_type),
                "description": self._get_tool_description(agent.agent_type),
                "config": agent.config,
                "is_active": agent.is_active
            }
            tools.append(tool_info)
        
        return tools
    
    def _get_tool_name(self, agent_type: ToolAgentType) -> str:
        """도구 타입별 이름 반환"""
        name_map = {
            ToolAgentType.SQL_AGENT: "SQL 분석 도구",
            ToolAgentType.WEB_SEARCH: "웹 검색 도구",
            ToolAgentType.FILE_PROCESSOR: "파일 처리 도구",
            ToolAgentType.API_CONNECTOR: "API 연동 도구"
        }
        return name_map.get(agent_type, "알 수 없는 도구")
    
    def _get_tool_description(self, agent_type: ToolAgentType) -> str:
        """도구 타입별 설명 반환"""
        desc_map = {
            ToolAgentType.SQL_AGENT: "한국 통계청 데이터베이스에서 SQL 쿼리를 실행하여 통계 정보를 조회합니다",
            ToolAgentType.WEB_SEARCH: "웹에서 정보를 검색하여 최신 데이터를 수집합니다",
            ToolAgentType.FILE_PROCESSOR: "파일을 업로드하고 처리하여 데이터를 분석합니다",
            ToolAgentType.API_CONNECTOR: "외부 API와 연동하여 실시간 데이터를 가져옵니다"
        }
        return desc_map.get(agent_type, "도구에 대한 설명이 없습니다")