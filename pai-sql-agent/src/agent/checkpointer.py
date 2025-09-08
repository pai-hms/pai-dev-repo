"""PostgreSQL-based checkpointer for LangGraph agent persistence."""

import json
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repository import CheckpointRepository
from src.database.connection import get_async_session


class PostgreSQLCheckpointSaver(BaseCheckpointSaver):
    """PostgreSQL-based checkpoint saver following data sovereignty principle."""
    
    def __init__(self):
        self.repository: Optional[CheckpointRepository] = None
    
    async def _get_repository(self) -> CheckpointRepository:
        """Get repository instance with async session."""
        if not self.repository:
            # This is a simplified approach - in production, use dependency injection
            async for session in get_async_session():
                self.repository = CheckpointRepository(session)
                break
        return self.repository
    
    async def aget(
        self, 
        config: Dict[str, Any], 
        checkpoint_id: Optional[str] = None
    ) -> Optional[Checkpoint]:
        """Get checkpoint asynchronously."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
        
        repository = await self._get_repository()
        
        if checkpoint_id:
            checkpoint_record = await repository.get_checkpoint(thread_id, checkpoint_id)
        else:
            checkpoint_record = await repository.get_latest_checkpoint(thread_id)
        
        if not checkpoint_record:
            return None
        
        # Deserialize state data
        state_data = json.loads(checkpoint_record.state_data)
        metadata = json.loads(checkpoint_record.metadata) if checkpoint_record.metadata else {}
        
        return Checkpoint(
            v=1,
            id=checkpoint_record.checkpoint_id,
            ts=checkpoint_record.created_at.isoformat(),
            channel_values=state_data.get("channel_values", {}),
            channel_versions=state_data.get("channel_versions", {}),
            versions_seen=state_data.get("versions_seen", {}),
            pending_sends=state_data.get("pending_sends", []),
        )
    
    def get(
        self, 
        config: Dict[str, Any], 
        checkpoint_id: Optional[str] = None
    ) -> Optional[Checkpoint]:
        """Get checkpoint synchronously (not recommended)."""
        raise NotImplementedError("Use async version instead")
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> Dict[str, Any]:
        """Save checkpoint asynchronously."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        checkpoint_id = checkpoint.id or str(uuid.uuid4())
        
        # Serialize checkpoint data
        state_data = {
            "channel_values": checkpoint.channel_values,
            "channel_versions": checkpoint.channel_versions,
            "versions_seen": checkpoint.versions_seen,
            "pending_sends": checkpoint.pending_sends,
        }
        
        repository = await self._get_repository()
        await repository.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state_data=state_data,
            metadata=metadata.__dict__ if metadata else None,
        )
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> Dict[str, Any]:
        """Save checkpoint synchronously (not recommended)."""
        raise NotImplementedError("Use async version instead")
    
    async def alist(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = 10,
        before: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], Checkpoint, CheckpointMetadata]]:
        """List checkpoints asynchronously."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return []
        
        # This is a simplified implementation
        # In production, you'd want to implement proper pagination and filtering
        repository = await self._get_repository()
        
        # Get recent checkpoints (simplified query)
        # You would need to implement a proper list method in the repository
        latest_checkpoint = await repository.get_latest_checkpoint(thread_id)
        
        if not latest_checkpoint:
            return []
        
        # Convert to required format
        state_data = json.loads(latest_checkpoint.state_data)
        metadata = json.loads(latest_checkpoint.metadata) if latest_checkpoint.metadata else {}
        
        checkpoint = Checkpoint(
            v=1,
            id=latest_checkpoint.checkpoint_id,
            ts=latest_checkpoint.created_at.isoformat(),
            channel_values=state_data.get("channel_values", {}),
            channel_versions=state_data.get("channel_versions", {}),
            versions_seen=state_data.get("versions_seen", {}),
            pending_sends=state_data.get("pending_sends", []),
        )
        
        config_with_checkpoint = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": latest_checkpoint.checkpoint_id,
            }
        }
        
        checkpoint_metadata = CheckpointMetadata(**metadata) if metadata else CheckpointMetadata()
        
        return [(config_with_checkpoint, checkpoint, checkpoint_metadata)]
    
    def list(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = 10,
        before: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], Checkpoint, CheckpointMetadata]]:
        """List checkpoints synchronously (not recommended)."""
        raise NotImplementedError("Use async version instead")
