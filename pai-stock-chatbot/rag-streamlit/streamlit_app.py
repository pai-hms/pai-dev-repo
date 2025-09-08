# rag-streamlit/streamlit_app.py
import streamlit as st
import httpx
import uuid
import json

st.set_page_config(page_title="PAI Stock Chatbot", layout="centered")

# API URL - rag-server에서 실행되는 FastAPI 서버
API_URL = "http://localhost:8000/api/v1"

def test_api_connection():
    """API 연결 테스트"""
    try:
        response = httpx.get("http://localhost:8000/", timeout=5.0)
        return response.status_code == 200
    except:
        return False

def stream_chat(message: str, thread_id: str):
    """개선된 채팅 스트리밍"""
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/stream",
            json={"message": message, "threadId": thread_id},  # camelCase 사용
            timeout=30.0,
            headers={"Accept": "text/event-stream"}
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_text():
                    if chunk.strip():
                        try:
                            # JSON 파싱 시도
                            chunk_data = json.loads(chunk.strip())
                            if "content" in chunk_data:
                                yield chunk_data["content"]
                            elif "error" in chunk_data:
                                yield f"❌ 오류: {chunk_data['error']}"
                            else:
                                yield chunk.strip()
                        except json.JSONDecodeError:
                            # JSON이 아닌 경우 그대로 출력
                            yield chunk.strip()
            else:
                yield f"❌ API 오류: {response.status_code} - {response.text}"
    except httpx.TimeoutException:
        yield "❌ 요청 시간 초과"
    except httpx.ConnectError:
        yield "❌ 서버 연결 실패"
    except Exception as e:
        yield f"❌ 연결 오류: {str(e)}"

def process_user_input(prompt: str):
    """실시간 토큰 스트리밍 처리"""
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # AI 응답
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # 첫 토큰 수신 시간 측정
        import time
        start_time = time.time()
        first_token_time = None
        
        chunk_count = 0
        for chunk in stream_chat(prompt, st.session_state.thread_id):
            chunk_count += 1
            if chunk:  # 빈 청크 무시
                # 첫 토큰 수신 시간 기록
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                    st.caption(f"⚡ 첫 토큰 수신: {first_token_time:.2f}초")
                
                full_response += chunk
                # 실시간 타이핑 효과 (커서 없이 즉시 표시)
                response_placeholder.markdown(full_response + "▌")
                
                # 매우 짧은 지연으로 자연스러운 타이핑 효과
                time.sleep(0.01)
        
        # 최종 응답 (커서 제거)
        response_placeholder.markdown(full_response)
        
        # 성능 정보 표시
        total_time = time.time() - start_time
        if st.session_state.get("debug_mode", False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"📊 청크 수: {chunk_count}")
            with col2:
                st.caption(f"⏱️ 총 시간: {total_time:.2f}초")
            with col3:
                if first_token_time:
                    st.caption(f"🚀 첫 토큰: {first_token_time:.2f}초")
    
    # 응답 저장
    if full_response.strip():
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        st.error("응답을 받지 못했습니다. 다시 시도해주세요.")

# 메인 앱
st.title("🤖 PAI Stock Chatbot")

# API 연결 상태 확인
if test_api_connection():
    st.success("✅ 백엔드 연결됨")
else:
    st.error("❌ 백엔드 연결 실패 - FastAPI 서버를 먼저 실행해주세요")
    st.code("cd rag-server && uv run uvicorn webapp.main:app --reload")
    st.stop()

# 세션 ID 초기화
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

# 예시 질문 처리를 위한 flag
if "processing_example" not in st.session_state:
    st.session_state.processing_example = False

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 예시 질문이 클릭되었을 때 처리
if st.session_state.processing_example:
    example_question = st.session_state.example_question
    process_user_input(example_question)
    # 처리 완료 후 플래그 리셋
    st.session_state.processing_example = False
    st.rerun()

# 채팅 입력
if prompt := st.chat_input("주식에 대해 물어보세요 (예: AAPL 주가, 100*1.5 계산)"):
    process_user_input(prompt)

# 사이드바 - 간단한 컨트롤
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 디버그 모드 토글
    st.session_state.debug_mode = st.checkbox(
        "🔍 디버그 모드", 
        value=st.session_state.get("debug_mode", False),
        help="스트리밍 성능 정보를 표시합니다"
    )
    
    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    
    st.subheader("💡 예시 질문")
    examples = [
        "AAPL 주가 알려줘",
        "100 * 1.5 계산해줘", 
        "테슬라 주가는?",
        "내 이름은 홍길동이야"
    ]
    
    for example in examples:
        if st.button(f"📝 {example}", key=f"ex_{example}"):
            # 예시 질문을 세션 상태에 저장하고 처리 플래그 설정
            st.session_state.example_question = example
            st.session_state.processing_example = True
            st.rerun()

    # 추가 정보
    st.markdown("---")
    st.caption(f"세션 ID: {st.session_state.thread_id[:8]}...")
    st.caption(f"메시지 수: {len(st.session_state.messages)}")