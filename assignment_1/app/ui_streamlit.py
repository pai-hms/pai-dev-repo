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
    
    # 주식 종목별 세션 추가
    st.subheader("주식 종목 세션 추가")
    
    # 인기 주식 종목 버튼들
    popular_stocks = ["애플", "테슬라", "구글", "마이크로소프트", "아마존", "메타", "넷플릭스", "엔비디아"]
    
    cols = st.columns(2)
    for i, stock in enumerate(popular_stocks):
        with cols[i % 2]:
            if st.button(f"{stock}", key=f"stock_{stock}"):
                if stock not in st.session_state.sessions:
                    st.session_state.sessions[stock] = {
                        "thread_id": str(uuid.uuid4()),
                        "messages": [{"role": "assistant", "content": f"안녕하세요! {stock} 주식 정보를 도와주는 에이전트입니다."}]
                    }
                    st.rerun()
                else:
                    st.warning(f"{stock} 세션이 이미 존재합니다.")
    
    st.markdown("---")
    
    # 커스텀 세션 추가
    st.subheader("커스텀 세션 추가")
    new_session_name = st.text_input("세션 이름")
    if st.button("세션 추가"):
        if new_session_name and new_session_name not in st.session_state.sessions:
            st.session_state.sessions[new_session_name] = {
                "thread_id": str(uuid.uuid4()),
                "messages": [{"role": "assistant", "content": "안녕하세요! 주식 가격이나 계산을 도와주는 에이전트입니다."}]
            }
            st.rerun()
        elif new_session_name in st.session_state.sessions:
            st.warning("이미 존재하는 세션 이름입니다.")
    
    # 기존 세션 목록
    st.subheader("활성 세션")
    if st.session_state.sessions:
        for session_name in list(st.session_state.sessions.keys()):
            col1, col2 = st.columns([3, 1])
            with col1:
                # 주식 종목인지 확인하여 아이콘 표시
                if session_name in popular_stocks:
                    st.text(f"{session_name}")
                else:
                    st.text(f"{session_name}")
            with col2:
                if st.button("삭제", key=f"delete_{session_name}", help="세션 삭제"):
                    del st.session_state.sessions[session_name]
                    st.rerun()
    else:
        st.info("활성 세션이 없습니다.")

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

# 주식 종목별 독립성 테스트
if len(st.session_state.sessions) >= 2:
    st.markdown("---")
    if st.button("주식 종목별 독립성 테스트"):
        st.subheader("주식 종목별 세션 독립성 테스트")
        
        sessions = list(st.session_state.sessions.items())
        session1_name, session1 = sessions[0]
        session2_name, session2 = sessions[1]
        
        st.write(f"**세션 1**: {session1_name} (ID: {session1['thread_id'][:8]}...)")
        st.write(f"**세션 2**: {session2_name} (ID: {session2['thread_id'][:8]}...)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**{session1_name} 세션**: {session1_name} 주가 알려줘")
            with st.spinner("주가 조회 중..."):
                response1_chunks = []
                for chunk in stream_api_response(f"{session1_name} 주가 알려줘", session1["thread_id"]):
                    response1_chunks.append(chunk)
                response1 = "".join(response1_chunks)
            st.write(response1)
        
        with col2:
            st.write(f"**{session2_name} 세션**: {session2_name} 주가 알려줘")
            with st.spinner("주가 조회 중..."):
                response2_chunks = []
                for chunk in stream_api_response(f"{session2_name} 주가 알려줘", session2["thread_id"]):
                    response2_chunks.append(chunk)
                response2 = "".join(response2_chunks)
            st.write(response2)
        
        st.markdown("---")
        
        # 독립성 확인 테스트
        col3, col4 = st.columns(2)
        
        with col3:
            st.write(f"**{session1_name} 세션**: 방금 조회한 {session2_name} 주가가 얼마였지?")
            with st.spinner("기억 확인 중..."):
                response3_chunks = []
                for chunk in stream_api_response(f"방금 조회한 {session2_name} 주가가 얼마였지?", session1["thread_id"]):
                    response3_chunks.append(chunk)
                response3 = "".join(response3_chunks)
            st.write(response3)
        
        with col4:
            st.write(f"**{session2_name} 세션**: 방금 조회한 {session1_name} 주가가 얼마였지?")
            with st.spinner("기억 확인 중..."):
                response4_chunks = []
                for chunk in stream_api_response(f"방금 조회한 {session1_name} 주가가 얼마였지?", session2["thread_id"]):
                    response4_chunks.append(chunk)
                response4 = "".join(response4_chunks)
            st.write(response4)
            
            # 독립성 검증
            if ("모르" in response3 or "없" in response3) and ("모르" in response4 or "없" in response4):
                st.success(" 세션이 독립적으로 동작합니다! 각 세션은 자신의 주식 정보만 기억합니다.")
            elif session2_name.lower() in response3.lower() or session1_name.lower() in response4.lower():
                st.error(" 세션 간 정보가 공유되고 있습니다! 독립성에 문제가 있습니다.")
            else:
                st.warning(" 예상과 다른 결과입니다.")
        
        # 추가 테스트: 각 세션에서 자신의 주식 정보 확인
        st.markdown("---")
        st.subheader("각 세션의 주식 정보 확인")
        
        col5, col6 = st.columns(2)
        
        with col5:
            st.write(f"**{session1_name} 세션**: {session1_name} 주가 다시 알려줘")
            with st.spinner("재확인 중..."):
                response5_chunks = []
                for chunk in stream_api_response(f"{session1_name} 주가 다시 알려줘", session1["thread_id"]):
                    response5_chunks.append(chunk)
                response5 = "".join(response5_chunks)
            st.write(response5)
        
        with col6:
            st.write(f"**{session2_name} 세션**: {session2_name} 주가 다시 알려줘")
            with st.spinner("재확인 중..."):
                response6_chunks = []
                for chunk in stream_api_response(f"{session2_name} 주가 다시 알려줘", session2["thread_id"]):
                    response6_chunks.append(chunk)
                response6 = "".join(response6_chunks)
            st.write(response6)