"""FastAPI dependencies following dependency injection principle."""

from typing import AsyncGenerator

from src.agent.graph import AgentService
from src.database.connection import get_async_session, db_manager
from src.database.repository import BudgetRepository, PopulationRepository, QueryRepository


async def get_agent_service() -> AgentService:
    """Dependency to get agent service instance."""
    return AgentService()


async def get_budget_repository() -> AsyncGenerator[BudgetRepository, None]:
    """Dependency to get budget repository."""
    async for session in get_async_session():
        yield BudgetRepository(session)


async def get_population_repository() -> AsyncGenerator[PopulationRepository, None]:
    """Dependency to get population repository."""
    async for session in get_async_session():
        yield PopulationRepository(session)


async def get_query_repository() -> AsyncGenerator[QueryRepository, None]:
    """Dependency to get query repository."""
    async for session in get_async_session():
        yield QueryRepository(session)


async def startup_event():
    """Application startup event."""
    await db_manager.initialize()


async def shutdown_event():
    """Application shutdown event."""
    await db_manager.close()
