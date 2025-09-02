# tests/test_agent.py
import pytest
from langchain_core.messages import HumanMessage
from app.agents.graph import agent_executor

@pytest.mark.asyncio
async def test_stock_price_query():
    query = "엔비디아 5주랑 아마존 8주를 두명이 돈을 모아 사려고 하는데, 각자 얼마나 돈 챙겨야 해?"
    
    # Create a config dictionary with a unique thread_id for the test
    config = {"configurable": {"thread_id": "test-thread-1"}}
    
    # Pass the config dictionary to the ainvoke call
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
    query = "애플 주가 알려줘"
    config = {"configurable": {"thread_id": "test-thread-2"}}
    
    final_state = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )
    
    last_message = final_state["messages"][-1]
    content = last_message.content
    
    # 답변이 비어있지 않은지 확인
    assert len(content) > 0
    # 주가 정보가 포함되어 있는지 확인 (숫자가 있는지)
    assert any(char.isdigit() for char in content)

@pytest.mark.asyncio
async def test_calculation_query():
    """계산 관련 쿼리 테스트"""
    query = "테슬라 10주 사려면 얼마나 필요해?"
    config = {"configurable": {"thread_id": "test-thread-3"}}
    
    final_state = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )
    
    last_message = final_state["messages"][-1]
    content = last_message.content
    
    # 계산 결과가 포함되어 있는지 확인
    assert any(char.isdigit() for char in content)

@pytest.mark.asyncio
async def test_agent_memory_sequence():
    """에이전트 기억능력 순차 테스트"""
    thread_id = "memory-sequence-test"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 대화 시퀀스 정의
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
    
    # 검증: 마지막 응답에서 이전 정보들을 참조하는지 확인
    last_response = responses[-1]
    assert "테슬라" in last_response or "Tesla" in last_response or "TSLA" in last_response
    assert any(char.isdigit() for char in last_response)
    
    # 두 번째 응답에서 계산이 제대로 되었는지 확인
    second_response = responses[1]
    assert any(char.isdigit() for char in second_response)
    assert ("원" in second_response or "$" in second_response)