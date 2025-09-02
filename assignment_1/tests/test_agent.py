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