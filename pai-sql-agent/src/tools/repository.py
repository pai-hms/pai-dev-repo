"""
DB CRUD 작업을 담당하는 레포지토리
데이터 접근 계층
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from src.database.repository import BaseRepository
from src.tools.domains import ToolAgent, ToolAgentType, ToolAgentStatus
from src.tools.entities import ToolAgentEntity


class ToolAgentRepository(BaseRepository[int, ToolAgent]):
    """Tool Agent 레포지토리"""

    entity = ToolAgentEntity
    
    async def find_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """챗봇 ID로 Tool Agent 목록 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.chatbot_id == chatbot_id
            ).order_by(ToolAgentEntity.created_at.desc())
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return [entity.to_domain() for entity in entities]
    
    async def find_by_chatbot_and_type(self, chatbot_id: int, agent_type: ToolAgentType) -> List[ToolAgent]:
        """챗봇 ID와 에이전트 타입으로 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.chatbot_id == chatbot_id,
                ToolAgentEntity.agent_type == agent_type.value
            ).order_by(ToolAgentEntity.created_at.desc())
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return [entity.to_domain() for entity in entities]
    
    async def find_active_by_chatbot_id(self, chatbot_id: int) -> List[ToolAgent]:
        """활성 상태의 Tool Agent만 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.chatbot_id == chatbot_id,
                ToolAgentEntity.is_active == True,
                ToolAgentEntity.status == ToolAgentStatus.ACTIVE.value
            ).order_by(ToolAgentEntity.created_at.desc())
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return [entity.to_domain() for entity in entities]
    
    async def find_by_id(self, tool_agent_id: int) -> Optional[ToolAgent]:
        """ID로 단일 Tool Agent 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.tool_agent_id == tool_agent_id
            )
            
            result = await session.execute(stmt)
            entity = result.scalar_one_or_none()
            
            return entity.to_domain() if entity else None
    
    async def create(self, tool_agent: ToolAgent) -> ToolAgent:
        """새로운 Tool Agent 생성"""
        async with self.session_factory() as session:
            entity = ToolAgentEntity.from_domain(tool_agent)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            
            return entity.to_domain()
    
    async def update(self, tool_agent: ToolAgent) -> ToolAgent:
        """Tool Agent 업데이트"""
        async with self.session_factory() as session:
            stmt = update(ToolAgentEntity).where(
                ToolAgentEntity.tool_agent_id == tool_agent.tool_agent_id
            ).values(
                config=tool_agent.config,
                is_active=tool_agent.is_active,
                status=tool_agent.status.value,
                name=tool_agent.name,
                description=tool_agent.description,
                version=tool_agent.version,
                usage_count=tool_agent.usage_count,
                last_used_at=tool_agent.last_used_at,
                avg_response_time=tool_agent.avg_response_time,
                updated_at=tool_agent.updated_at
            )
            
            await session.execute(stmt)
            await session.commit()
            
            # 업데이트된 엔티티 조회
            return await self.find_by_id(tool_agent.tool_agent_id)
    
    async def delete(self, tool_agent_id: int) -> bool:
        """Tool Agent 삭제"""
        async with self.session_factory() as session:
            stmt = delete(ToolAgentEntity).where(
                ToolAgentEntity.tool_agent_id == tool_agent_id
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0
    
    async def count_by_chatbot_id(self, chatbot_id: int) -> int:
        """챗봇별 Tool Agent 개수 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.chatbot_id == chatbot_id
            )
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return len(entities)
    
    async def find_by_status(self, status: ToolAgentStatus) -> List[ToolAgent]:
        """상태별 Tool Agent 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.status == status.value
            ).order_by(ToolAgentEntity.updated_at.desc())
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return [entity.to_domain() for entity in entities]
    
    async def find_recently_used(self, limit: int = 10) -> List[ToolAgent]:
        """최근 사용된 Tool Agent 조회"""
        async with self.session_factory() as session:
            stmt = select(ToolAgentEntity).where(
                ToolAgentEntity.last_used_at.isnot(None)
            ).order_by(ToolAgentEntity.last_used_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            return [entity.to_domain() for entity in entities]
    
    async def update_usage_stats(self, tool_agent_id: int, response_time: float = None) -> bool:
        """사용 통계 업데이트"""
        tool_agent = await self.find_by_id(tool_agent_id)
        if not tool_agent:
            return False
        
        tool_agent.record_usage(response_time)
        await self.update(tool_agent)
        return True