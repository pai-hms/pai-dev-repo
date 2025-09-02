# app/ui_streamlit.py
import streamlit as st
import httpx
import uuid
import asyncio
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Stock-Bot",
    layout="wide"
)

# --- Constants ---
API_URL = "http://127.0.0.1:8000/api/v1"

# --- Session State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 주식 가격이나 계산을 도와주는 에이전트 입니다."}
    ]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# --- Sidebar for Session Management ---
with st.sidebar:
    st.header("세션 관리")
    
    # 현재 세션 정보
    st.subheader("현재 세션")
    st.text(f"ID: {st.session_state.thread_id[:8]}...")
    
    # 새 세션 시작
    if st.button("새 세션 시작"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = [
            {"role": "assistant", "content": "새로운 세션이 시작되었습니다!"}
        ]
        st.rerun()
    
    # 세션 정보 조회
    if st.button("세션 정보 조회"):
        try:
            response = httpx.get(f"{API_URL}/session/{st.session_state.thread_id}")
            if response.status_code == 200:
                info = response.json()
                st.json(info)
            else:
                st.error("세션 정보를 가져올 수 없습니다.")
        except Exception as e:
            st.error(f"오류: {e}")

# --- Main Chat Interface ---
st.title("주가 계산 챗봇 (Stock-Bot)")

# --- Helper Function for API Call ---
def stream_api_response(prompt: str, thread_id: str):
    """개선된 API 호출 함수 - 에러 처리 강화"""
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/stream",
            json={"message": prompt, "thread_id": thread_id},
            timeout=60.0,  # 타임아웃 설정
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_text():
                    if chunk.strip():  # 빈 청크 필터링
                        yield chunk
            else:
                yield f"API 오류: {response.status_code}"
    except httpx.TimeoutException:
        yield "요청 시간이 초과되었습니다. 다시 시도해주세요."
    except Exception as e:
        yield f"연결 오류: {str(e)}"

# --- Chat Interface ---
# 메시지 히스토리 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
if prompt := st.chat_input("주식에 대해 물어보세요! (예: 애플 주가, 테슬라 10주 계산)"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답 스트리밍
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            full_response = st.write_stream(
                stream_api_response(prompt, st.session_state.thread_id)
            )
    
    # 완성된 응답을 세션에 저장
    if full_response:
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- Footer ---
st.markdown("---")