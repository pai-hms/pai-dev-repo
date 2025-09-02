# app/ui_streamlit.py
import streamlit as st
import httpx
import uuid

st.set_page_config(
    page_title="Stock-Bot",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000/api/v1"

# 세션 상태 관리
if "sessions" not in st.session_state:
    st.session_state.sessions = {}

def stream_api_response(prompt: str, thread_id: str):
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/stream",
            json={"message": prompt, "thread_id": thread_id},
            timeout=60.0,
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_text():
                    if chunk.strip():
                        yield chunk
            else:
                yield f"API 오류: {response.status_code}"
    except Exception as e:
        yield f"연결 오류: {str(e)}"

# 사이드바
with st.sidebar:
    st.header("세션 관리")
    
    # 새 세션 추가
    new_session_name = st.text_input("세션 이름")
    if st.button("세션 추가"):
        if new_session_name and new_session_name not in st.session_state.sessions:
            st.session_state.sessions[new_session_name] = {
                "thread_id": str(uuid.uuid4()),
                "messages": [{"role": "assistant", "content": "안녕하세요! 주식 가격이나 계산을 도와주는 에이전트입니다."}]
            }
            st.rerun()
    
    # 기존 세션 목록
    for session_name in list(st.session_state.sessions.keys()):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(session_name)
        with col2:
            if st.button("삭제", key=f"delete_{session_name}"):
                del st.session_state.sessions[session_name]
                st.rerun()

st.title("주가 계산 챗봇")

# 세션이 있으면 탭으로 표시
if st.session_state.sessions:
    session_names = list(st.session_state.sessions.keys())
    tabs = st.tabs(session_names)
    
    for tab, session_name in zip(tabs, session_names):
        with tab:
            session_data = st.session_state.sessions[session_name]
            
            # 세션 정보
            st.text(f"세션 ID: {session_data['thread_id'][:8]}...")
            
            # 입력창을 가장 위에 고정
            prompt = st.chat_input("주식에 대해 물어보세요", key=f"input_{session_name}")
            
            # 메시지 처리 (입력 처리)
            if prompt:
                # 사용자 메시지 추가
                session_data["messages"].append({"role": "user", "content": prompt})
                
                # AI 응답 생성
                with st.spinner("생각 중..."):
                    full_response_chunks = []
                    for chunk in stream_api_response(prompt, session_data["thread_id"]):
                        full_response_chunks.append(chunk)
                    full_response = "".join(full_response_chunks)
                
                # 응답 저장
                if full_response:
                    session_data["messages"].append({"role": "assistant", "content": full_response})
                
                st.rerun()
            
            # 스크롤 가능한 대화내용 영역
            st.markdown("### 대화 내용")
            chat_container = st.container(height=500)
            
            with chat_container:
                for message in session_data["messages"]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

else:
    st.info("좌측에서 새 세션을 추가해주세요")

# 독립성 테스트
if len(st.session_state.sessions) >= 2:
    st.markdown("---")
    if st.button("독립성 테스트"):
        st.subheader("테스트 결과")
        
        sessions = list(st.session_state.sessions.items())
        session1_name, session1 = sessions[0]
        session2_name, session2 = sessions[1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**{session1_name}**: {session1_name} 주가 알려줘")
            with st.spinner("생각 중..."):
                response1_chunks = []
                for chunk in stream_api_response(f"{session1_name} 주가 알려줘", session1["thread_id"]):
                    response1_chunks.append(chunk)
                response1 = "".join(response1_chunks)
            st.write(response1)
        
        with col2:
            st.write(f"**{session2_name}**: 방금 조회한 {session1_name} 주가가 얼마였지?")
            with st.spinner("생각 중..."):
                response2_chunks = []
                for chunk in stream_api_response(f"방금 조회한 {session1_name} 주가가 얼마였지?", session2["thread_id"]):
                    response2_chunks.append(chunk)
                response2 = "".join(response2_chunks)
            st.write(response2)
            
            if "모르" in response2 or "없" in response2:
                st.success("세션이 독립적으로 동작합니다")
            else:
                st.warning("세션 독립성에 문제가 있을 수 있습니다")