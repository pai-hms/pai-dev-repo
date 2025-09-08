"""Repository pattern implementation for database operations."""

from typing import List, Optional, Dict, Any
import json
from datetime import datetime

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, text

from .models import BudgetCategory, BudgetItem, PopulationData, QueryHistory, AgentCheckpoint
from .connection import db_manager


class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session


class BudgetRepository(BaseRepository):
    """Repository for budget-related data operations."""
    
    async def get_budget_categories(self) -> List[BudgetCategory]:
        """Get all budget categories."""
        result = await self.session.execute(select(BudgetCategory))
        return result.scalars().all()
    
    async def get_budget_items_by_year(self, year: int) -> List[BudgetItem]:
        """Get budget items for specific year."""
        result = await self.session.execute(
            select(BudgetItem).where(BudgetItem.year == year)
        )
        return result.scalars().all()
    
    async def get_budget_items_by_category(self, category_code: str) -> List[BudgetItem]:
        """Get budget items by category code."""
        result = await self.session.execute(
            select(BudgetItem).where(BudgetItem.category_code == category_code)
        )
        return result.scalars().all()


class PopulationRepository(BaseRepository):
    """Repository for population data operations."""
    
    async def get_population_by_year(self, year: int) -> List[PopulationData]:
        """Get population data for specific year."""
        result = await self.session.execute(
            select(PopulationData).where(PopulationData.year == year)
        )
        return result.scalars().all()
    
    async def get_population_by_region(self, region_code: str) -> List[PopulationData]:
        """Get population data by region code."""
        result = await self.session.execute(
            select(PopulationData).where(PopulationData.region_code == region_code)
        )
        return result.scalars().all()


class QueryRepository(BaseRepository):
    """Repository for query history operations."""
    
    async def save_query_history(
        self,
        user_question: str,
        generated_sql: str,
        execution_result: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ) -> QueryHistory:
        """Save query execution history."""
        query_history = QueryHistory(
            user_question=user_question,
            generated_sql=generated_sql,
            execution_result=execution_result,
            success=1 if success else 0,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
        )
        self.session.add(query_history)
        await self.session.commit()
        await self.session.refresh(query_history)
        return query_history
    
    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Get recent query history."""
        result = await self.session.execute(
            select(QueryHistory)
            .order_by(QueryHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


class SQLExecutor:
    """SQL query executor with data sovereignty principle."""
    
    async def execute_sql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dictionaries."""
        try:
            # Use raw connection for direct SQL execution
            connection = await db_manager.get_connection()
            try:
                result = await connection.fetch(query)
                return [dict(row) for row in result]
            finally:
                await db_manager.release_connection(connection)
        except Exception as e:
            raise Exception(f"SQL execution error: {str(e)}")
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        schema_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = $1 
        ORDER BY ordinal_position;
        """
        return await self.execute_sql_query(schema_query)
    
    async def get_all_table_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get schema information for all tables."""
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
        """
        
        connection = await db_manager.get_connection()
        try:
            tables_result = await connection.fetch(tables_query)
            schemas = {}
            
            for table_row in tables_result:
                table_name = table_row['table_name']
                schema_info = await self.get_table_schema(table_name)
                schemas[table_name] = schema_info
            
            return schemas
        finally:
            await db_manager.release_connection(connection)


class CheckpointRepository(BaseRepository):
    """Repository for agent checkpoint operations."""
    
    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentCheckpoint:
        """Save agent checkpoint."""
        checkpoint = AgentCheckpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state_data=json.dumps(state_data),
            metadata=json.dumps(metadata) if metadata else None,
        )
        self.session.add(checkpoint)
        await self.session.commit()
        await self.session.refresh(checkpoint)
        return checkpoint
    
    async def get_checkpoint(
        self, thread_id: str, checkpoint_id: str
    ) -> Optional[AgentCheckpoint]:
        """Get specific checkpoint."""
        result = await self.session.execute(
            select(AgentCheckpoint)
            .where(
                AgentCheckpoint.thread_id == thread_id,
                AgentCheckpoint.checkpoint_id == checkpoint_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_latest_checkpoint(self, thread_id: str) -> Optional[AgentCheckpoint]:
        """Get latest checkpoint for thread."""
        result = await self.session.execute(
            select(AgentCheckpoint)
            .where(AgentCheckpoint.thread_id == thread_id)
            .order_by(AgentCheckpoint.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
