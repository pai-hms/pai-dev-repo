# tests/test_multi_session.py
import pytest
import asyncio
from langchain_core.messages import HumanMessage
from app.core.session_manager import SessionManager

@pytest.mark.asyncio
async def test_multi_session_isolation():
    """여러 세션이 독립적으로 동작하는지 테스트"""
    session_manager = SessionManager()
    
    # 두 개의 독립적인 세션 생성
    session1_id = "test-session-1"
    session2_id = "test-session-2"
    
    # 동시에 두 세션에서 다른 작업 수행
    async def session1_task():
        responses = []
        async for chunk in session_manager.stream_chat("애플 5주 계산해서 알려줘", session1_id):
            responses.append(chunk)
        return "".join(responses)
    
    async def session2_task():
        responses = []
        async for chunk in session_manager.stream_chat("테슬라 3주 계산해서 알려줘", session2_id):
            responses.append(chunk)
        return "".join(responses)
    
    # 동시 실행
    result1, result2 = await asyncio.gather(session1_task(), session2_task())
    
    # 각 세션이 독립적인 결과를 가져야 함
    assert "애플" in result1 or "Apple" in result1 or "AAPL" in result1
    assert "테슬라" in result2 or "Tesla" in result2 or "TSLA" in result2
    
    # 세션 정보 확인
    info1 = await session_manager.get_session_info(session1_id)
    info2 = await session_manager.get_session_info(session2_id)
    
    assert info1['thread_id'] == session1_id
    assert info2['thread_id'] == session2_id
    assert info1['message_count'] >= 1
    assert info2['message_count'] >= 1

@pytest.mark.asyncio
async def test_concurrent_sessions():
    """동시 다중 세션 처리 테스트"""
    session_manager = SessionManager()
    
    async def create_session_task(session_id: str, query: str):
        responses = []
        async for chunk in session_manager.stream_chat(query, session_id):
            responses.append(chunk)
        return session_id, "".join(responses)
    
    # 10개의 동시 세션 생성
    tasks = []
    for i in range(10):
        session_id = f"concurrent-test-{i}"
        query = f"애플 주가 {i}번째 조회"
        tasks.append(create_session_task(session_id, query))
    
    # 모든 작업 동시 실행
    results = await asyncio.gather(*tasks)
    
    # 모든 세션이 성공적으로 처리되었는지 확인
    assert len(results) == 10
    
    for session_id, response in results:
        assert len(response) > 0
        info = await session_manager.get_session_info(session_id)
        assert info is not None
        assert info['thread_id'] == session_id