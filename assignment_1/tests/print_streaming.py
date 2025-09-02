"""
LangGraph 기본 스트리밍 기능 테스트
주가 조회, 계산, 기억 기능을 테스트합니다.

LangGraph 내장 스트리밍 기능:
1. stream() - 기본 스트리밍 (updates 모드)
2. stream_mode="values" - 상태 값 스트리밍
3. output_keys - 특정 키만 스트리밍
4. interrupt_before/after - 중단점 설정
5. astream_events() - 이벤트 기반 스트리밍
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from app.agents.graph import create_memory_agent_executor



async def test_basic_streaming():
    """기본 스트리밍 - 주가 조회 및 계산 테스트"""
    print("=== 기본 스트리밍 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "basic-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "애플 5주 사려면 얼마나 필요해?"
        print(f"테스트: {test_message}\n")
        
        # 기본 stream() 메서드 사용
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config
        ):
            for key, value in event.items():
                print(f"[{key}]")
                if "messages" in value:
                    value["messages"][-1].pretty_print()
                
        print("\n기본 스트리밍 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_values_mode():
    """values 모드 - 상태 값 스트리밍 테스트"""
    print("\n=== values 모드 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "values-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "테슬라 주가 알려줘"
        print(f"테스트: {test_message}\n")
        
        # values 모드로 스트리밍
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            stream_mode="values"
        ):
            for key, value in event.items():
                print(f"[{key}]")
                if key == "messages":
                    print(f"메시지 개수: {len(value)}")
                    if value:
                        value[-1].pretty_print()
                
        print("\nvalues 모드 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_output_keys():
    """output_keys 옵션 - 메시지만 스트리밍 테스트"""
    print("\n=== output_keys 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "output-keys-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "구글 주가 알려줘"
        print(f"테스트: {test_message}\n")
        
        # messages만 출력하도록 설정
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            output_keys=["messages"]
        ):
            for key, value in event.items():
                print(f"[{key}]")
                if "messages" in value:
                    value["messages"][-1].pretty_print()
                
        print("\noutput_keys 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_interrupt_before():
    """interrupt_before - 도구 실행 전 중단 테스트"""
    print("\n=== interrupt_before 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "interrupt-before-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "마이크로소프트 주가 알려줘"
        print(f"테스트: {test_message}")
        print("도구 실행 전에 중단됩니다.\n")
        
        # tools 노드 이전에 중단
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            stream_mode="updates",
            interrupt_before=["tools"]
        ):
            for key, value in event.items():
                print(f"[{key}]")
                if key == "__interrupt__":
                    print("중단됨 - tools 노드 실행 전")
                elif "messages" in value:
                    print(f"메시지 개수: {len(value['messages'])}")
                    value["messages"][-1].pretty_print()
                    
        print("\ninterrupt_before 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_interrupt_after():
    """interrupt_after - 도구 실행 후 중단 테스트"""
    print("\n=== interrupt_after 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "interrupt-after-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "애플 주가 알려줘"
        print(f"테스트: {test_message}")
        print("도구 실행 후에 중단됩니다.\n")
        
        # tools 노드 이후에 중단
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message)]},
            config=config,
            stream_mode="updates",
            interrupt_after=["tools"]
        ):
            for key, value in event.items():
                print(f"[{key}]")
                if key == "__interrupt__":
                    print("중단됨 - tools 노드 실행 후")
                elif "messages" in value:
                    print(f"메시지 개수: {len(value['messages'])}")
                    value["messages"][-1].pretty_print()
                    
        print("\ninterrupt_after 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_memory_functionality():
    """기억 기능 테스트 - 이전 대화 기억"""
    print("\n=== 기억 기능 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "memory-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        # 첫 번째 질문
        test_message1 = "내 이름은 김철수야"
        print(f"첫 번째 질문: {test_message1}\n")
        
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message1)]},
            config=config
        ):
            for key, value in event.items():
                if "messages" in value:
                    value["messages"][-1].pretty_print()
        
        print("\n" + "="*50)
        
        # 두 번째 질문 (기억 테스트)
        test_message2 = "내 이름이 뭐라고 했지?"
        print(f"두 번째 질문: {test_message2}\n")
        
        async for event in app.astream(
            input={"messages": [HumanMessage(content=test_message2)]},
            config=config
        ):
            for key, value in event.items():
                if "messages" in value:
                    value["messages"][-1].pretty_print()
                    
        print("\n기억 기능 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

async def test_token_streaming():
    """토큰 스트리밍 - 실시간 응답 출력"""
    print("\n=== 토큰 스트리밍 테스트 ===\n")
    
    try:
        app = create_memory_agent_executor()
        thread_id = "token-streaming-test"
        config = {'configurable': {'thread_id': thread_id}}
        
        test_message = "구글 주가 알려줘"
        print(f"테스트: {test_message}")
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
                    
        print("\n토큰 스트리밍 테스트 완료!")
        
    except Exception as e:
        print(f"오류: {e}")



if __name__ == "__main__":
    print("LangGraph 기본 스트리밍 기능 테스트\n")
    
    # 기본 스트리밍 기능 테스트
    asyncio.run(test_basic_streaming())
    asyncio.run(test_values_mode())
    asyncio.run(test_output_keys())
    asyncio.run(test_interrupt_before())
    asyncio.run(test_interrupt_after())
    asyncio.run(test_memory_functionality())
    asyncio.run(test_token_streaming())
    
    print("\n모든 테스트 완료!")