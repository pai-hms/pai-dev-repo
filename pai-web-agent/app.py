import streamlit as st
import os
import time
import asyncio
import uuid
import json
import csv
import io
import pandas as pd
from typing import Dict, Any, List, Generator
from agent import create_agent, SupervisedAgent
from tools import create_tavily_tool

# 페이지 설정
st.set_page_config(
    page_title="PAI Web Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 고급 CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        background-color: #fafafa;
    }
    .streaming-message {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .tool-usage {
        background-color: #e8f4fd;
        border: 1px solid #2196f3;
        border-radius: 0.25rem;
        padding: 0.5rem;
        margin: 0.25rem 0;
        font-size: 0.9rem;
    }
    .metrics-container {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    .metric-box {
        text-align: center;
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """세션 상태 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"streamlit_session_{uuid.uuid4().hex[:8]}"
    if "streaming_response" not in st.session_state:
        st.session_state.streaming_response = ""
    if "conversation_stats" not in st.session_state:
        st.session_state.conversation_stats = {
            "total_queries": 0,
            "successful_responses": 0,
            "tool_usage_count": 0,
            "avg_response_time": 0.0
        }
    if "api_keys_set" not in st.session_state:
        st.session_state.api_keys_set = False


def check_api_keys() -> bool:
    """API 키 확인"""
    openai_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    return bool(openai_key and tavily_key and 
                openai_key != "test_openai_key_here" and 
                tavily_key != "test_tavily_key_here")


def display_api_key_setup():
    """API 키 설정 UI"""
    st.markdown('<div class="main-header">🔑 API 키 설정</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ API 키가 설정되지 않았습니다. 환경 변수를 설정하거나 아래에 입력해주세요.")
    
    with st.form("api_keys_form"):
        st.subheader("API 키 입력")
        
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="OpenAI Platform에서 발급받은 API 키를 입력하세요"
        )
        
        tavily_key = st.text_input(
            "Tavily API Key", 
            type="password",
            help="Tavily에서 발급받은 API 키를 입력하세요"
        )
        
        submitted = st.form_submit_button("API 키 설정")
        
        if submitted:
            if openai_key and tavily_key:
                os.environ["OPENAI_API_KEY"] = openai_key
                os.environ["TAVILY_API_KEY"] = tavily_key
                st.session_state.api_keys_set = True
                st.success("✅ API 키가 설정되었습니다!")
                st.rerun()
            else:
                st.error("❌ 모든 API 키를 입력해주세요.")
    
    # API 키 발급 안내
    st.markdown("---")
    st.subheader("📋 API 키 발급 방법")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **OpenAI API Key**
        1. [OpenAI Platform](https://platform.openai.com/api-keys) 방문
        2. 계정 생성 또는 로그인
        3. API Keys 섹션에서 새 키 생성
        4. 생성된 키를 복사하여 위에 입력
        """)
    
    with col2:
        st.markdown("""
        **Tavily API Key**
        1. [Tavily](https://tavily.com/) 방문
        2. 계정 생성 또는 로그인
        3. Dashboard에서 API 키 확인
        4. 키를 복사하여 위에 입력
        
        💡 **월 1,000회 무료 제공**
        """)


def display_conversation_stats():
    """대화 통계 표시"""
    stats = st.session_state.conversation_stats
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 질문 수",
            value=stats["total_queries"],
            delta=None
        )
    
    with col2:
        success_rate = (stats["successful_responses"] / max(stats["total_queries"], 1)) * 100
        st.metric(
            label="성공률",
            value=f"{success_rate:.1f}%",
            delta=None
        )
    
    with col3:
        st.metric(
            label="도구 사용 횟수",
            value=stats["tool_usage_count"],
            delta=None
        )
    
    with col4:
        st.metric(
            label="평균 응답 시간",
            value=f"{stats['avg_response_time']:.2f}초",
            delta=None
        )


def display_streaming_response(response_generator: Generator, placeholder, metadata_placeholder=None):
    """모든 스트리밍 모드 지원하는 응답 표시"""
    full_response = ""
    step_data = []
    token_buffer = ""
    
    # 스트리밍 설정 가져오기
    settings = st.session_state.get("stream_settings", {})
    stream_mode = settings.get("mode", "messages")
    show_metadata = settings.get("show_metadata", False)
    
    # 다중 모드인지 확인
    is_multi_mode = isinstance(stream_mode, list)
    
    for chunk in response_generator:
        # 메타데이터가 포함된 경우 처리
        if isinstance(chunk, dict) and "data" in chunk:
            step_info = chunk
            actual_data = chunk["data"]
            
            if show_metadata and metadata_placeholder:
                step_data.append(step_info)
                display_metadata_info(step_data, metadata_placeholder)
        else:
            actual_data = chunk
            step_info = None
        
        # 다중 모드 처리
        if is_multi_mode:
            # (mode, data) 튜플 형태
            if isinstance(actual_data, tuple) and len(actual_data) == 2:
                mode, data = actual_data
                full_response = process_mode_data(mode, data, placeholder, full_response, token_buffer)
            else:
                # 오류 처리
                display_error_info(actual_data, placeholder)
        else:
            # 단일 모드 처리
            full_response = process_mode_data(stream_mode, actual_data, placeholder, full_response, token_buffer)
        
        time.sleep(0.05)  # 스트리밍 효과
    
    return full_response


def process_mode_data(mode: str, data, placeholder, current_response: str, token_buffer: str = ""):
    """모드별 데이터 처리 통합 함수"""
    if mode == "values":
        return process_values_mode(data, placeholder, current_response)
    elif mode == "updates":
        return process_updates_mode(data, placeholder, current_response)
    elif mode == "debug":
        return process_debug_mode(data, placeholder, current_response)
    elif mode == "messages":
        return process_messages_mode(data, placeholder, current_response, token_buffer)
    elif mode == "custom":
        return process_custom_mode(data, placeholder, current_response)
    else:
        return current_response


def process_values_mode(data, placeholder, current_response):
    """VALUES 모드 데이터 처리"""
    if isinstance(data, dict) and "messages" in data and data["messages"]:
        last_message = data["messages"][-1]
        
        if hasattr(last_message, 'content') and last_message.content:
            response = last_message.content
            
            with placeholder.container():
                st.markdown(f"""
                <div class="streaming-message">
                    <div style="font-weight: bold; margin-bottom: 0.5rem;">
                        🔹 VALUES 모드: 전체 상태 ({len(data["messages"])}개 메시지)
                    </div>
                    <div>{response}</div>
                </div>
                """, unsafe_allow_html=True)
            
            return response
    
    return current_response


def process_updates_mode(data, placeholder, current_response):
    """UPDATES 모드 데이터 처리"""
    if isinstance(data, dict) and "messages" in data:
        new_messages = data["messages"]
        
        if new_messages:
            for msg in new_messages:
                if hasattr(msg, 'content') and msg.content:
                    current_response += msg.content
            
            with placeholder.container():
                st.markdown(f"""
                <div class="streaming-message">
                    <div style="font-weight: bold; margin-bottom: 0.5rem;">
                        🔸 UPDATES 모드: 증분 업데이트 (+{len(new_messages)}개 메시지)
                    </div>
                    <div>{current_response}</div>
                </div>
                """, unsafe_allow_html=True)
    
    return current_response


def process_debug_mode(data, placeholder, current_response):
    """DEBUG 모드 데이터 처리"""
    if isinstance(data, dict):
        # DEBUG 모드는 더 상세한 정보를 포함
        debug_info = []
        
        if "messages" in data and data["messages"]:
            last_message = data["messages"][-1]
            if hasattr(last_message, 'content') and last_message.content:
                current_response = last_message.content
            
            debug_info.append(f"메시지 수: {len(data['messages'])}")
        
        # 추가 디버그 정보 수집
        for key, value in data.items():
            if key not in ["messages"] and value:
                debug_info.append(f"{key}: {str(value)[:50]}...")
        
        with placeholder.container():
            st.markdown(f"""
            <div class="streaming-message">
                <div style="font-weight: bold; margin-bottom: 0.5rem;">
                    🔍 DEBUG 모드: 상세 정보
                </div>
                <div style="font-size: 0.8em; color: #666; margin-bottom: 0.5rem;">
                    {' | '.join(debug_info)}
                </div>
                <div>{current_response}</div>
            </div>
            """, unsafe_allow_html=True)
    
    return current_response


def process_messages_mode(data, placeholder, current_response, token_buffer):
    """MESSAGES 모드 - LLM 토큰 스트리밍 처리 (사용자 친화적)"""
    
    # 에러 처리 먼저 확인
    if isinstance(data, dict) and "error" in data:
        with placeholder.container():
            st.error(f"🔤 오류: {data['error']}")
        return current_response
    
    # messages 모드에서는 (message_chunk, metadata) 튜플이 반환됨
    if isinstance(data, tuple) and len(data) == 2:
        message_chunk, metadata = data
        
        # 토큰 내용 추출 (실제 AI 응답만)
        token_content = ""
        if hasattr(message_chunk, 'content') and message_chunk.content:
            # 도구 결과나 시스템 메시지는 제외하고 AI 응답만 표시
            content = message_chunk.content
            
            # 깔끔한 모드에서는 도구 결과 필터링
            settings = st.session_state.get("stream_settings", {})
            clean_mode = settings.get("clean_mode", True)
            
            if clean_mode:
                # JSON 형태의 도구 결과는 필터링
                if not (content.startswith('{"') and '"results"' in content):
                    token_content = content
                    current_response += token_content
            else:
                # 모든 내용 표시
                token_content = content
                current_response += token_content
        
        # 메타데이터에서 노드 정보 확인
        node_info = metadata.get("langgraph_node", "unknown") if isinstance(metadata, dict) else "unknown"
        
        # AI 응답만 표시 (도구 노드 제외)
        if token_content and node_info != "tools":
            with placeholder.container():
                st.markdown(f"""
                <div class="streaming-message">
                    <div style="font-weight: bold; margin-bottom: 0.5rem; color: #1f77b4;">
                        🤖 AI 응답 생성 중...
                    </div>
                    <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; white-space: pre-wrap; line-height: 1.6;">
                        {current_response}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # 도구 사용 중일 때 별도 표시
        elif node_info == "tools":
            # 현재 도메인 설정 정보 가져오기
            settings = st.session_state.get("stream_settings", {})
            include_domains = settings.get("include_domains", [])
            exclude_domains = settings.get("exclude_domains", [])
            search_depth = settings.get("search_depth", "basic")
            max_results = settings.get("max_results", 5)
            
            # 도메인 필터링 정보 생성
            domain_info = ""
            if include_domains:
                domain_info += f"포함 도메인: {', '.join(include_domains[:2])}{'...' if len(include_domains) > 2 else ''} | "
            if exclude_domains:
                domain_info += f"제외 도메인: {', '.join(exclude_domains[:2])}{'...' if len(exclude_domains) > 2 else ''} | "
            domain_info += f"깊이: {search_depth} | 결과: {max_results}개"
            
            with placeholder.container():
                st.markdown(f"""
                <div class="tool-usage">
                    <div style="font-weight: bold; color: #ff9800; margin-bottom: 0.5rem;">
                        🔍 정보 검색 중...
                    </div>
                    <div style="color: #666; font-style: italic; margin-bottom: 0.25rem;">
                        Tavily 검색 엔진을 통해 최신 정보를 찾고 있습니다.
                    </div>
                    <div style="font-size: 0.8em; color: #888; background: #f0f0f0; padding: 0.25rem; border-radius: 0.25rem;">
                        {domain_info}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        return current_response
    
    # 다른 형태의 메시지 처리
    elif data and hasattr(data, 'content'):
        content = data.content if data.content else ""
        
        # 깔끔한 모드 설정 확인
        settings = st.session_state.get("stream_settings", {})
        clean_mode = settings.get("clean_mode", True)
        
        if content:
            if clean_mode:
                # JSON 형태의 도구 결과는 제외 (더 엄격한 필터링)
                is_json_tool_result = (
                    content.startswith('{"') or 
                    content.startswith("{'") or
                    ('"query"' in content and '"results"' in content) or
                    ('"url"' in content and '"title"' in content and '"content"' in content)
                )
                
                if not is_json_tool_result:
                    current_response += content
            else:
                # 모든 내용 표시
                current_response += content
            
            with placeholder.container():
                st.markdown(f"""
                <div class="streaming-message">
                    <div style="font-weight: bold; margin-bottom: 0.5rem; color: #1f77b4;">
                        🤖 AI 응답
                    </div>
                    <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; white-space: pre-wrap; line-height: 1.6;">
                        {current_response}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        return current_response
    
    return current_response


def process_custom_mode(data, placeholder, current_response):
    """CUSTOM 모드 - 커스텀 데이터 처리"""
    if data:
        with placeholder.container():
            st.markdown(f"""
            <div class="streaming-message">
                <div style="font-weight: bold; margin-bottom: 0.5rem;">
                    🎯 CUSTOM 모드: 커스텀 데이터
                </div>
                <div style="background: #e8f4fd; padding: 0.5rem; border-radius: 0.25rem; border-left: 4px solid #2196f3;">
                    <pre>{str(data)}</pre>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    return current_response


def display_error_info(data, placeholder):
    """오류 정보 표시"""
    with placeholder.container():
        st.error(f"스트리밍 오류: {data}")


def detect_tool_usage(data, placeholder):
    """도구 사용 감지 (모든 모드 공통)"""
    # messages 모드가 아닌 경우에만 도구 사용 표시
    settings = st.session_state.get("stream_settings", {})
    stream_mode = settings.get("mode", "messages")
    
    if stream_mode == "messages":
        return  # messages 모드에서는 별도 처리하므로 여기서는 스킵
    
    if isinstance(data, dict) and "messages" in data:
        messages = data["messages"] if isinstance(data["messages"], list) else [data["messages"]]
        
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                st.session_state.conversation_stats["tool_usage_count"] += 1
                
                with placeholder.container():
                    st.markdown("""
                    <div class="tool-usage">
                        🔍 Tavily 검색 도구를 사용하여 최신 정보를 검색하고 있습니다...
                    </div>
                    """, unsafe_allow_html=True)
                break


def display_metadata_info(step_data, metadata_placeholder):
    """메타데이터 정보 표시"""
    if not step_data:
        return
    
    latest_step = step_data[-1]
    
    with metadata_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("단계", latest_step.get("step_number", 0))
        
        with col2:
            elapsed = latest_step.get("elapsed_time", 0)
            st.metric("경과 시간", f"{elapsed:.2f}초")
        
        with col3:
            data_size = latest_step.get("data_size", 0)
            st.metric("데이터 크기", f"{data_size:,} 문자")
        
        with col4:
            mode = latest_step.get("stream_mode", "unknown")
            st.metric("모드", mode.upper())
        
        # 단계별 진행 상황 차트
        if len(step_data) > 1:
            
            df = pd.DataFrame([
                {
                    "단계": step["step_number"],
                    "데이터 크기": step["data_size"],
                    "경과 시간": step["elapsed_time"]
                }
                for step in step_data
            ])
            
            st.line_chart(df.set_index("단계"))


def process_streaming_query(user_input: str):
    """스트리밍 방식으로 쿼리 처리"""
    start_time = time.time()
    
    # 사용자 메시지 추가
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": time.strftime("%H:%M:%S")
    })
    
    # 통계 업데이트
    st.session_state.conversation_stats["total_queries"] += 1
    
    # 스트리밍 응답 컨테이너
    response_placeholder = st.empty()
    
    try:
        # 스트리밍 설정 가져오기
        stream_settings = st.session_state.get("stream_settings", {})
        stream_mode = stream_settings.get("mode", "messages")
        show_metadata = stream_settings.get("show_metadata", False)
        
        # 스트리밍 응답 생성
        if show_metadata:
            response_generator = st.session_state.agent.stream_response_with_metadata(
                user_input,
                thread_id=st.session_state.thread_id,
                stream_mode=stream_mode
            )
        else:
            response_generator = st.session_state.agent.stream_response(
                user_input,
                thread_id=st.session_state.thread_id,
                stream_mode=stream_mode
            )
        
        # 스트리밍 응답 표시
        final_response = display_streaming_response(response_generator, response_placeholder)
        
        # 응답이 있든 없든 처리 완료로 간주
        if final_response and final_response.strip():
            response_content = final_response.strip()
        else:
            # messages 모드에서는 토큰이 실시간으로 표시되므로 빈 응답도 정상
            response_content = "응답이 완료되었습니다."
        
        # 최종 응답 메시지 추가
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_content,
            "timestamp": time.strftime("%H:%M:%S")
        })
        
        # 성공 통계 업데이트
        st.session_state.conversation_stats["successful_responses"] += 1
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        current_avg = st.session_state.conversation_stats["avg_response_time"]
        total_queries = st.session_state.conversation_stats["total_queries"]
        
        # 평균 응답 시간 업데이트
        new_avg = ((current_avg * (total_queries - 1)) + response_time) / total_queries
        st.session_state.conversation_stats["avg_response_time"] = new_avg
        
        # 최종 완료 메시지 표시 (messages 모드에서는 이미 실시간으로 표시됨)
        if stream_mode != "messages":
            response_placeholder.empty()
            
    except Exception as e:
        error_msg = f"처리 중 오류가 발생했습니다: {str(e)}"
        
        st.session_state.messages.append({
            "role": "error",
            "content": error_msg,
            "timestamp": time.strftime("%H:%M:%S")
        })
        
        response_placeholder.empty()


def display_advanced_sidebar():
    """사이드바 표시"""
    with st.sidebar:
        st.markdown('<div class="main-header">🤖 PAI Web Agent</div>', unsafe_allow_html=True)
        
        # API 키 상태 표시
        st.subheader("🔐 API 상태")
        if check_api_keys():
            st.success("✅ API 키 설정됨")
        else:
            st.error("🔑 API 키 필요")
            if st.button("🔑 API 키 설정하기", use_container_width=True):
                st.session_state.show_api_setup = True
                st.rerun()
        
        # 에이전트 설정
        st.subheader("🔧 에이전트 설정")
        
        # 모델 선택
        model_options = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        selected_model = st.selectbox(
            "모델 선택",
            model_options,
            index=0,
            help="사용할 OpenAI 모델을 선택하세요"
        )
        
        # 온도 설정
        temperature = st.slider(
            "창의성 수준 (Temperature)",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="높을수록 더 창의적인 응답"
        )
        
        
        # 검색 설정
        st.subheader("🔍 검색 설정")
        
        search_depth = st.selectbox(
            "검색 깊이",
            ["basic", "advanced"],
            index=0,
            help="advanced는 더 정확하지만 비용이 2배"
        )
        
        max_results = st.slider(
            "최대 검색 결과 수",
            min_value=1,
            max_value=10,
            value=5,
            help="더 많은 결과는 더 정확하지만 느림"
        )
        
        # 스트리밍 설정 (messages 모드 고정)
        st.subheader("🔄 스트리밍 설정")
        st.info("💬 **Messages 모드**: 실시간 토큰 스트리밍으로 빠른 응답 제공")
        stream_mode = "messages"  # 고정
        
        show_metadata = st.checkbox(
            "메타데이터 표시",
            value=False,
            help="단계별 실행 시간, 데이터 크기 등 상세 정보 표시"
        )
        
        clean_mode = st.checkbox(
            "깔끔한 모드",
            value=True,
            help="도구 결과나 시스템 메시지를 숨기고 AI 응답만 표시"
        )
        
        # 도메인 필터링 상태 표시
        st.subheader("🌐 도메인 필터링 상태")
        
        # 현재 설정된 도메인 표시 (tools.py에서 하드코딩된 값)
        current_include_domains = ["*.go.kr", "*.or.kr"]
        current_exclude_domains = []
        
        st.info(f"""
        **현재 적용된 도메인 필터링:**
        - 🏛️ **포함 도메인**: {', '.join(current_include_domains)}
        - 🚫 **제외 도메인**: {'없음' if not current_exclude_domains else ', '.join(current_exclude_domains)}
        
        """)
        
        
        
        # 세션 상태에 설정 저장
        if "stream_settings" not in st.session_state:
            st.session_state.stream_settings = {}
        
        st.session_state.stream_settings.update({
            "mode": stream_mode,
            "show_metadata": show_metadata,
            "clean_mode": clean_mode,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_domains": current_include_domains,
            "exclude_domains": current_exclude_domains
        })
        
        # 에이전트 재초기화
        if st.button("🔄 설정 적용", use_container_width=True):
            try:
                st.session_state.agent = SupervisedAgent(
                    model_name=selected_model,
                    temperature=temperature,
                )
                st.success("✅ 설정이 적용되었습니다!")
            except Exception as e:
                st.error(f"❌ 설정 적용 실패: {str(e)}")
        
        st.markdown("---")
        
        # 대화 관리
        st.subheader("💬 대화 관리")
        
        if st.button("🗑️ 대화 기록 삭제", use_container_width=True):
            # 새로운 thread_id 생성으로 메모리 초기화
            st.session_state.thread_id = f"streamlit_session_{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.session_state.conversation_stats = {
                "total_queries": 0,
                "successful_responses": 0,
                "tool_usage_count": 0,
                "avg_response_time": 0.0
            }
            st.success("✅ 대화 기록이 완전히 삭제되었습니다!")
            st.rerun()
        
        # 대화 내보내기
        if st.session_state.messages:
            export_format = st.selectbox("내보내기 형식", ["TXT", "JSON", "CSV"])
            
            if export_format == "TXT":
                export_data = "\n".join([
                    f"[{msg.get('timestamp', 'N/A')}] {msg['role'].upper()}: {msg['content']}"
                    for msg in st.session_state.messages
                ])
                file_ext = "txt"
                mime_type = "text/plain"
            
            elif export_format == "JSON":
                export_data = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
                file_ext = "json"
                mime_type = "application/json"
            
            else:  # CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["timestamp", "role", "content"])
                for msg in st.session_state.messages:
                    writer.writerow([msg.get('timestamp', 'N/A'), msg['role'], msg['content']])
                export_data = output.getvalue()
                file_ext = "csv"
                mime_type = "text/csv"
            
            st.download_button(
                label=f"💾 {export_format} 다운로드",
                data=export_data,
                file_name=f"chat_history_{st.session_state.thread_id}.{file_ext}",
                mime=mime_type,
                use_container_width=True
            )


def display_advanced_chat():
    """고급 채팅 인터페이스"""
    # 대화 통계 표시
    st.subheader("📊 대화 통계")
    display_conversation_stats()
    
    st.markdown("---")
    
    # 채팅 기록
    st.subheader("💬 대화 기록")
    
    # 채팅 컨테이너
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 안녕하세요! 질문을 입력해주세요.")
        
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            timestamp = message.get("timestamp", "")
            
            if role == "user":
                st.chat_message("user").write(f"**[{timestamp}]** {content}")
            elif role == "assistant":
                st.chat_message("assistant").write(f"**[{timestamp}]** {content}")
            else:  # error
                st.chat_message("assistant").error(f"**[{timestamp}]** {content}")
    
    # 입력 영역
    st.markdown("---")
    
    # 빠른 질문 버튼
    st.subheader("⚡ 빠른 질문")
    
    col1, col2, col3 = st.columns(3)
    
    quick_questions = [
        "2025년 대한민국 예산 규모는?",
        "최근 통계청 발표 주요 지표는?",
        "정부 정책 최신 동향은?",
        "공공기관 채용 정보는?",
        "지방자치단체 재정 현황은?",
        "국가통계포털 최신 데이터는?"
    ]
    
    for i, question in enumerate(quick_questions):
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(question, key=f"quick_{i}", use_container_width=True):
                process_streaming_query(question)
                st.rerun()
    
    # 사용자 입력
    st.subheader("✍️ 질문 입력")
    
    user_input = st.text_area(
        "질문을 입력하세요:",
        placeholder="예: 대구광역시 2025년 재정 현황은? 또는 통계청 최근 인구 통계는?",
        height=100,
        key="user_input"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 스트리밍 전송", use_container_width=True, type="primary"):
            if user_input.strip():
                process_streaming_query(user_input.strip())
                st.rerun()
            else:
                st.warning("질문을 입력해주세요.")
    
    with col2:
        if st.button("🔄 입력 초기화", use_container_width=True):
            st.session_state.user_input = ""
            st.rerun()
    

def main():
    """고급 메인 애플리케이션"""
    initialize_session_state()
    
    # API 키 설정 상태 확인
    if "show_api_setup" not in st.session_state:
        st.session_state.show_api_setup = False
    
    # API 키 확인
    if not check_api_keys() and not st.session_state.api_keys_set:
        if not st.session_state.show_api_setup:
            st.session_state.show_api_setup = True
        display_api_key_setup()
        return
    
    # 에이전트 초기화
    if st.session_state.agent is None:
        try:
            with st.spinner("🤖 에이전트를 초기화하는 중..."):
                st.session_state.agent = create_agent()
            st.success("✅ 에이전트가 성공적으로 초기화되었습니다!")
        except Exception as e:
            st.error(f"❌ 에이전트 초기화 실패: {str(e)}")
            st.stop()
    
    # 사이드바 표시
    display_advanced_sidebar()
    
    # 메인 헤더
    st.markdown('<div class="main-header">🤖 PAI Web Agent</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 🌟 주요 기능
    - **🏛️ 공공기관 정보 특화**: *.go.kr, *.or.kr 도메인 우선 검색
    - **🔍 실시간 웹 검색**: Tavily API로 최신 정부/공공기관 정보 수집
    - **💬 스트리밍 응답**: 응답 생성 과정을 실시간으로 확인
    - **📊 신뢰할 수 있는 정보**: 공식 사이트 우선, 개인 블로그/SNS 제외
    - **🌐 도메인 필터링**: 정부기관, 공공기관 사이트만 검색 가능
    - **🎯 공공정보 빠른 질문**: 예산, 통계, 정책 등 미리 준비된 질문
    """)
    
    # 고급 채팅 인터페이스
    display_advanced_chat()


if __name__ == "__main__":
    main()