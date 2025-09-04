# rag-server/src/chat_session/entities.py
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Message:
    content: str
    role: str
    timestamp: datetime

@dataclass
class ChatSession:
    thread_id: str
    created_at: datetime
    last_accessed: datetime
    message_count: int = 0
    
    def increment_message_count(self):
        self.message_count += 1
        self.last_accessed = datetime.now()
