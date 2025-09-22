"""
실시간 토큰 스트리밍 Streamlit SQL Agent 앱
LangGraph의 실제 토큰 스트리밍을 활용한 개선된 UI
"""
import streamlit as st
import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Generator

# 페이지 설정 구성
st.set_page_config(
    page_title="PAI SQL Agent",
    page_icon="🤖",
    layout="centered"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# API URL 설정
def get_api_base_url():
    """환경에 따른 API URL 반환"""
    urls_to_try = [
        "http://app:8000",           # Docker 환경
        "http://localhost:8000",     # 로컬
        "http://127.0.0.1:8000"      # 대체
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(f"{url}/", timeout=2)
            if response.status_code == 200:
                return url
        except:
            continue
    
    return "http://localhost:8000"

API_BASE_URL = get_api_base_url()

# API 호출 함수 (통합 스트리밍)
def call_agent_stream(question: str) -> Generator[Dict[str, Any], None, None]:
    """통합 스트리밍 API 호출 - 멀티턴 대화 지원"""
    try:
        url = f"{API_BASE_URL}/api/agent/query"
        payload = {
            "question": question,
            "session_id": st.session_state.session_id,
            "thread_id": st.session_state.session_id  # 멀티턴 대화 지원
        }
        
        response = requests.post(url, json=payload, stream=True, timeout=30)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line and line.startswith(b'data: '):
                try:
                    data = json.loads(line[6:])
                    yield data
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        yield {"type": "error", "content": str(e)}

def check_api_health() -> bool:
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/data/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_database_info() -> Dict[str, Any]:
    """데이터베이스 정보 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/data/database-info", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

# ====== UI 구성 ======

# 헤더
st.title("🤖 PAI SQL Agent")
st.markdown("**한국 통계청 데이터 분석 AI 에이전트 - 실시간 스트리밍**")

# API 상태 확인
if check_api_health():
    st.success(f"✅ API 서버 연결됨")
else:
    st.error(f"❌ API 서버 연결 실패")

# 사이드바
with st.sidebar:
    st.header("📋 사용 가이드")
    
    st.markdown("""
    **인구 통계 질문 예시:**
    - 2023년 서울시 인구는?
    - 2022년 경기도 인구는?
    - 2020년 전국 시도별 평균 연령이 가장 높은 곳은?
    
    **가구/주택 통계:**
    - 2020년 전라남도 평균 가구원수는 얼마인가요?
    - 2020년 경기도 평균 가구원수는 얼마인가요?
    
    **사업체 통계:**
    - 2023년 부산시 사업체 수는?
    - 전국에서 사업체가 가장 많은 지역은?
    """)
    
    st.markdown("---")
    st.header("🗄️ 데이터베이스 정보")
    
    # 데이터베이스 정보 조회
    if st.button("🔍 데이터베이스 정보 조회", key="db_info"):
        with st.spinner("데이터베이스 정보 조회 중..."):
            db_info = get_database_info()
            
            if db_info.get("success"):
                st.success("✅ 데이터베이스 연결 성공!")
                
                # 테이블 정보 표시
                if "tables" in db_info:
                    st.write("**📊 테이블 정보:**")
                    for table in db_info["tables"]:
                        table_name = table.get("table_name", "Unknown")
                        row_count = table.get("row_count", 0)
                        st.write(f"• {table_name}: {row_count:,}개 레코드")
                
                # 샘플 데이터 표시
                if "sample_data" in db_info:
                    st.write("**📝 샘플 데이터:**")
                    st.code(db_info["sample_data"], language="text")
            else:
                st.error(f"❌ 데이터베이스 오류: {db_info.get('error', 'Unknown')}")
    
    st.markdown("---")
    
    # 세션 정보 간단 표시
    st.write(f"**세션 ID**: `{st.session_state.session_id[:8]}...`")

# 대화 기록 표시
st.markdown("---")
st.subheader("💬 대화")

# 기존 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # 도구 사용 정보 (AI 응답)
        if message["role"] == "assistant" and "used_tools" in message:
            if message["used_tools"]:
                with st.expander("🛠️ 사용된 도구"):
                    for i, tool in enumerate(message["used_tools"], 1):
                        tool_name = tool.get("tool_name", "Unknown")
                        success = tool.get("success", False)
                        status = "✅" if success else "❌"
                        st.write(f"{status} {i}. {tool_name}")
        
        # 스트리밍 정보 표시 (간소화)
        if message["role"] == "assistant" and "streaming_info" in message:
            info = message["streaming_info"]
            with st.expander("📊 스트리밍 정보"):
                st.write(f"🟢 토큰 수: {info.get('total_tokens', 0)}")
                st.write(f"🟣 도구 실행: {info.get('tools_executed', 0)}")
        

# 사용자 입력
if prompt := st.chat_input("센서스 데이터에 대해 질문해보세요..."):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(prompt)
    
    # AI 응답 생성 부분을 완전히 간소화
    with st.chat_message("assistant"):
        response_container = st.empty()
        
        # 간단한 Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 상세 로그 (접을 수 있음)
        with st.expander("🔍 상세 진행 로그", expanded=False):
            log_container = st.empty()
            log_content = []
        
        try:
            full_response = ""
            current_progress = 0
            used_tools = []
            streaming_info = {}
            
            with st.spinner("🤖 AI가 답변을 생성하는 중..."):
                for chunk in call_agent_stream(prompt):
                    chunk_type = chunk.get("type", "unknown")
                    
                    # AI 메시지 토큰 스트리밍
                    if chunk_type == "ai_message":
                        token_content = chunk.get("content", "")
                        full_response += token_content
                        response_container.write(full_response + "▌")
                    
                    # 도구 호출 시작
                    elif chunk_type == "tool_call":
                        tool_info = {
                            "tool_name": chunk.get("content", chunk.get("tool_name", "Unknown")),
                            "success": chunk.get("success", True)
                        }
                        used_tools.append(tool_info)
                        
                        current_progress = 50
                        progress_bar.progress(current_progress)
                        status_text.text(f"🔧 도구 실행 중: {tool_info['tool_name']}")
                        
                        # 로그 추가
                        current_time = datetime.now().strftime("%H:%M:%S")
                        log_content.append(f"도구 호출: {tool_info['tool_name']}")
                        log_text = "\n".join([f"[{current_time}] {msg}" for msg in log_content[-3:]])
                        log_container.text(log_text)
                    
                    # 도구 실행 결과
                    elif chunk_type == "tool_result":
                        current_progress = 90
                        progress_bar.progress(current_progress)
                        status_text.text("📊 데이터 조회 완료")
                        
                        # 로그 추가
                        current_time = datetime.now().strftime("%H:%M:%S")
                        log_content.append("데이터 조회 완료")
                        log_text = "\n".join([f"[{current_time}] {msg}" for msg in log_content[-3:]])
                        log_container.text(log_text)
                    
                    # 에러 처리
                    elif chunk_type == "error":
                        st.error(f"오류: {chunk.get('content', 'Unknown error')}")
                        break
        
            # 완료 후 정리
            if full_response:
                response_container.write(full_response)
                
                # 최종 진행률
                progress_bar.progress(100)
                status_text.text("✅ 완료!")
                
                # 성공적인 응답을 세션 상태에 저장 (간소화)
                assistant_message = {
                    "role": "assistant",
                    "content": full_response,
                    "used_tools": used_tools,
                    "streaming_info": {
                        "tools_executed": len(used_tools),
                        "total_tokens": len(full_response.split()) if full_response else 0
                    }
                }
                st.session_state.messages.append(assistant_message)
                
                # UI 정리
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
        
        except Exception as e:
            response_container.error(f"클라이언트 오류: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"죄송합니다. 클라이언트 오류가 발생했습니다: {str(e)}",
                "used_tools": []
            })

# 푸터
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "PAI SQL Agent v3.0.0 | 통합 실시간 스트리밍 | LangGraph + PostgreSQL + SGIS API"
    "</div>",
    unsafe_allow_html=True
)
