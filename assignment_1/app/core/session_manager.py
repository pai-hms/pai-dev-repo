# app/core/session_manager.py
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from ..agents.graph import create_memory_agent_executor
import weakref
import threading

class SessionManager:
    """멀티세션을 위한 비동기 세션 매니저"""
    
    def __init__(self, session_timeout: int = 3600):  # 1시간 타임아웃
        self._sessions: Dict[str, dict] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_lock = asyncio.Lock()
        self._session_timeout = session_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def get_session(self, thread_id: str) -> dict:
        """세션별 독립적인 agent_executor 반환"""
        
        # 세션별 락 생성 시 클린업 락으로 보호
        if thread_id not in self._session_locks:
            async with self._cleanup_lock: # 락 생성 시 동시성 제어
                if thread_id not in self._session_locks:
                    self._session_locks[thread_id] = asyncio.Lock()
        
        # 세션별 락으로 세션 데이터 보호
        async with self._session_locks[thread_id]: # 세션별 동시성 제어
            if thread_id not in self._sessions:
                # 새 세션 생성 (락으로 보호됨)
                self._sessions[thread_id] = {
                    'executor': create_memory_agent_executor(),
                    'created_at': datetime.now(),
                    'last_accessed': datetime.now(),
                    'message_count': 0
                }
                
                # 첫 번째 세션 생성 시 정리 작업 시작
                if self._cleanup_task is None:
                    self._cleanup_task = asyncio.create_task(self._cleanup_sessions())
            
            # 마지막 접근 시간 업데이트 (락으로 보호됨)
            self._sessions[thread_id]['last_accessed'] = datetime.now()
            return self._sessions[thread_id]
    
    async def stream_chat(self, message: str, thread_id: str):
        """세션별 독립적인 스트리밍 처리"""
        session = await self.get_session(thread_id)
        executor = session['executor']
        
        # 메시지 카운트 증가
        session['message_count'] += 1
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            async for event in executor.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v1"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield content
        except Exception as e:
            yield f"오류가 발생했습니다: {str(e)}"
    
    async def _cleanup_sessions(self):
        """비활성 세션 정리 (백그라운드 작업)"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분마다 정리
                
                # 클린업 작업 시 전역 락 적용 
                async with self._cleanup_lock: # 클린업 중 다른 작업 차단
                    current_time = datetime.now() 
                    expired_sessions = []
                    
                    for thread_id, session in self._sessions.items():
                        if (current_time - session['last_accessed']).seconds > self._session_timeout:
                            expired_sessions.append(thread_id)
                    
                    # 만료된 세션 제거
                    for thread_id in expired_sessions:
                        del self._sessions[thread_id]
                        if thread_id in self._session_locks:
                            del self._session_locks[thread_id]
                        print(f"세션 {thread_id} 정리 완료")
                        
            except Exception as e:
                print(f"세션 정리 중 오류: {e}")
    
    async def get_session_info(self, thread_id: str) -> Optional[dict]:
        """세션 정보 조회 - 없으면 자동 생성"""
        # 세션이 없으면 자동으로 생성
        if thread_id not in self._sessions:
            await self.get_session(thread_id)  # 세션 자동 생성
        
        if thread_id in self._sessions:
            session = self._sessions[thread_id]
            return {
                'thread_id': thread_id,
                'created_at': session['created_at'].isoformat(),
                'last_accessed': session['last_accessed'].isoformat(),
                'message_count': session['message_count'],
                'active': True
            }
        return None
    
    async def close_session(self, thread_id: str) -> bool:
        # 세션 종료 시 클린업 락으로 보호
        async with self._cleanup_lock:
            if thread_id in self._sessions:
                del self._sessions[thread_id]
                if thread_id in self._session_locks:
                    del self._session_locks[thread_id]
                return True
        return False

# 전역 세션 매니저 인스턴스
session_manager = SessionManager()