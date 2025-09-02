# tests/test_agent.py
import pytest
from langchain_core.messages import HumanMessage
from app.agents.graph import create_memory_agent_executor  # 변경된 import

@pytest.mark.asyncio
async def test_stock_price_query():
    """주식 가격 쿼리 테스트 - 멀티세션 방식"""
    # 각 테스트마다 독립적인 executor 생성
    agent_executor = create_memory_agent_executor()
    
    query = "엔비디아 5주랑 아마존 8주를 두명이 돈을 모아 사려고 하는데, 각자 얼마나 돈 챙겨야 해?"
    config = {"configurable": {"thread_id": "test-thread-1"}}
    
    final_state = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config 
    )
    
    last_message = final_state["messages"][-1]
    content = last_message.content
    
    print(f"\n테스트 질문: {query}")
    print(f"최종 답변: {content}")
    
    assert any(char.isdigit() for char in content)

@pytest.mark.asyncio
async def test_simple_stock_query():
    """간단한 주식 조회 테스트"""
    agent_executor = create_memory_agent_executor()  # 독립적인 executor
    
    query = "애플 주가 알려줘"
    config = {"configurable": {"thread_id": "test-thread-2"}}
    
    final_state = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )
    
    last_message = final_state["messages"][-1]
    content = last_message.content
    
    assert len(content) > 0
    assert any(char.isdigit() for char in content)

@pytest.mark.asyncio
async def test_calculation_query():
    """계산 관련 쿼리 테스트"""
    agent_executor = create_memory_agent_executor()  # 독립적인 executor
    
    query = "테슬라 10주 사려면 얼마나 필요해?"
    config = {"configurable": {"thread_id": "test-thread-3"}}
    
    final_state = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )
    
    last_message = final_state["messages"][-1]
    content = last_message.content
    
    assert any(char.isdigit() for char in content)

@pytest.mark.asyncio
async def test_agent_memory_sequence():
    """에이전트 기억능력 순차 테스트"""
    agent_executor = create_memory_agent_executor()  # 독립적인 executor
    
    thread_id = "memory-sequence-test"
    config = {"configurable": {"thread_id": thread_id}}
    
    conversations = [
        "테슬라 주가 알려줘",
        "그 주가로 5주 사려면 얼마나 필요해?",
        "아까 조회한 테슬라 주가가 얼마였지?",
        "테슬라 3주와 아까 조회한 주가로 계산해줘"
    ]
    
    responses = []
    
    for i, query in enumerate(conversations, 1):
        final_state = await agent_executor.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config=config
        )
        response = final_state["messages"][-1].content
        responses.append(response)
        
        print(f"\n{i}단계 질문: {query}")
        print(f"{i}단계 응답: {response}")
    
    # 검증
    last_response = responses[-1]
    assert "테슬라" in last_response or "Tesla" in last_response or "TSLA" in last_response
    assert any(char.isdigit() for char in last_response)
    
    second_response = responses[1]
    assert any(char.isdigit() for char in second_response)