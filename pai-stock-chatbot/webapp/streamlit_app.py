# webapp/streamlit_app.py - 간소화된 Streamlit 앱
import streamlit as st
import httpx
import uuid

st.set_page_config(page_title="PAI Stock Chatbot", layout="centered")

# API URL - 포트 확인 필요
API_URL = "http://localhost:8000/api/v1"

def test_api_connection():
    """API 연결 테스트"""
    try:
        response = httpx.get("http://localhost:8000/", timeout=5.0)
        return response.status_code == 200
    except:
        return False

def stream_chat(message: str, thread_id: str):
    """간단한 채팅 스트리밍"""
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/stream",
            json={"message": message, "thread_id": thread_id},
            timeout=30.0,
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_text():
                    if chunk.strip():
                        yield chunk
            else:
                yield f"API 오류: {response.status_code}"
    except Exception as e:
        yield f"연결 오류: {str(e)}"

# 메인 앱
st.title("🤖 PAI Stock Chatbot")

# API 연결 상태 확인
if test_api_connection():
    st.success("백엔드 연결됨")
else:
    st.error("백엔드 연결 실패 - FastAPI 서버를 먼저 실행해주세요")
    st.code("uv run uvicorn webapp.main:app --reload")
    st.stop()

# 세션 ID 초기화
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 채팅 입력
if prompt := st.chat_input("주식에 대해 물어보세요 (예: AAPL 주가, 100*1.5 계산)"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # AI 응답
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        for chunk in stream_chat(prompt, st.session_state.thread_id):
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
    
    # 응답 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 사이드바 - 간단한 컨트롤
with st.sidebar:
    st.header("설정")
    
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    
    st.subheader("예시 질문")
    examples = [
        "AAPL 주가 알려줘",
        "100 * 1.5 계산해줘", 
        "테슬라 주가는?",
        "내 이름은 홍길동이야"
    ]
    
    for example in examples:
        if st.button(f"{example}", key=f"ex_{example}"):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()