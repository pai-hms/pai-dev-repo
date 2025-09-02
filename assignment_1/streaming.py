#!/usr/bin/env python3
"""
LangGraph 스트리밍 테스트 스크립트
그래프 단계별 스트리밍을 확인할 수 있습니다.
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from app.agents.graph import create_memory_agent_executor

def format_message_details(event: dict) -> str:
    """메시지 상세 정보를 포맷팅"""
    try:
        if "data" in event:
            data = event["data"]
            if "chunk" in data:
                chunk = data["chunk"]
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    result = f"================================== Ai Message ==================================\n"
                    if hasattr(chunk, 'content') and chunk.content:
                        result += f"\n{chunk.content}\n"
                    result += f"Tool Calls:\n"
                    for tool_call in chunk.tool_calls:
                        result += f"  {tool_call.get('name', 'N/A')} ({tool_call.get('id', 'N/A')})\n"
                        result += f" Call ID: {tool_call.get('id', 'N/A')}\n"
                        result += f"  Args:\n"
                        for key, value in tool_call.get('args', {}).items():
                            result += f"    {key}: {value}\n"
                    return result
                elif hasattr(chunk, 'content') and chunk.content:
                    result = f"================================== Ai Message ==================================\n"
                    result += f"\n{chunk.content}\n"
                    return result
        return ""
    except Exception as e:
        return f"Error formatting message: {e}"

async def test_langgraph_stream():
    """LangGraph의 기본 stream() 메서드 테스트"""
    print("=== LangGraph stream() 메서드 테스트 ===\n")
    
    try:
        # 에이전트 실행기 생성
        app = create_memory_agent_executor()
        thread_id = "stream-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        # 테스트 메시지
        test_message = "애플 5주 사려면 얼마나 필요해?"
        print(f"테스트 메시지: {test_message}\n")
        
        # LangGraph의 기본 stream() 메서드 사용
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config
        ):
            for key, value in event.items():
                print(f"\n[ {key} ]\n")
                if "messages" in value:
                    # 가장 최근 메시지 pretty_print
                    value["messages"][-1].pretty_print()
                
        print("\nstream() 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def test_langgraph_stream_updates():
    """LangGraph의 stream() 메서드 - updates 모드 테스트"""
    print("\n=== LangGraph stream() - updates 모드 테스트 ===\n")
    
    try:
        # 에이전트 실행기 생성
        app = create_memory_agent_executor()
        thread_id = "stream-updates-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        # 테스트 메시지
        test_message = "테슬라 주가 알려줘"
        print(f"테스트 메시지: {test_message}\n")
        
        # updates 모드로 스트리밍
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            stream_mode="updates"
        ):
            for key, value in event.items():
                print(f"\n[ {key} ]\n")
                if "messages" in value:
                    # 메시지 개수와 마지막 메시지 출력
                    print(f"메시지 개수: {len(value['messages'])}")
                    value["messages"][-1].pretty_print()
                
        print("\nstream() - updates 모드 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def test_langgraph_stream_values():
    """LangGraph의 stream() 메서드 - values 모드 테스트"""
    print("\n=== LangGraph stream() - values 모드 테스트 ===\n")
    
    try:
        # 에이전트 실행기 생성
        app = create_memory_agent_executor()
        thread_id = "stream-values-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        # 테스트 메시지
        test_message = "구글 주가 알려줘"
        print(f"테스트 메시지: {test_message}\n")
        
        # values 모드로 스트리밍
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            stream_mode="values"
        ):
            for key, value in event.items():
                print(f"\n[ {key} ]\n")
                if key == "messages":
                    print(f"메시지 개수: {len(value)}")
                    # 마지막 메시지만 출력
                    if value:
                        value[-1].pretty_print()
                
        print("\nstream() - values 모드 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def test_langgraph_stream_output_keys():
    """LangGraph의 stream() 메서드 - output_keys 옵션 테스트"""
    print("\n=== LangGraph stream() - output_keys 옵션 테스트 ===\n")
    
    try:
        # 에이전트 실행기 생성
        app = create_memory_agent_executor()
        thread_id = "stream-output-keys-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        # 테스트 메시지
        test_message = "마이크로소프트 주가 알려줘"
        print(f"테스트 메시지: {test_message}\n")
        
        # messages만 출력하도록 설정
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            output_keys=["messages"]
        ):
            for key, value in event.items():
                print(f"\n[ {key} ]\n")
                if "messages" in value:
                    value["messages"][-1].pretty_print()
                
        print("\nstream() - output_keys 옵션 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_streaming():
    """간단한 LLM 토큰 스트리밍만 테스트"""
    print("\n=== 간단한 LLM 스트리밍 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "simple-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "테슬라 주가 알려줘"
        print(f"테스트 메시지: {test_message}\n")
        print("AI 응답: ", end="", flush=True)
        
        # LLM 토큰만 스트리밍
        async for event in app.astream_events(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            version="v1"
        ):
            if event["event"] == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    print(content, end="", flush=True)
                    
        print("\n간단한 스트리밍 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")

async def test_pretty_print_messages():
    """메시지 pretty_print 테스트"""
    print("\n=== 메시지 Pretty Print 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "pretty-print-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "애플 주가와 구글 주가를 비교해줘"
        print(f"테스트 메시지: {test_message}\n")
        
        # astream으로 메시지 흐름 확인
        async for state_map in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config
        ):
            for key, state in state_map.items():
                print(f"\n--- 노드: {key} ---")
                if 'messages' in state and state['messages']:
                    last_message = state['messages'][-1]
                    print("메시지 타입:", type(last_message).__name__)
                    print("메시지 내용:")
                    last_message.pretty_print()
                print("-" * 40)
                    
        print("\nPretty Print 테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("LangGraph 스트리밍 테스트 시작\n")
    
    # LangGraph 내장 스트리밍 기능 테스트
    asyncio.run(test_langgraph_stream())
    asyncio.run(test_langgraph_stream_updates())
    asyncio.run(test_langgraph_stream_values())
    asyncio.run(test_langgraph_stream_output_keys())
    
    # 기존 테스트들
    asyncio.run(test_simple_streaming())
    asyncio.run(test_pretty_print_messages())
    
    print("\n모든 테스트 완료!")
