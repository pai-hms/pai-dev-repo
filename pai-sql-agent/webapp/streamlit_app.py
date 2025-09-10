"""
간단하고 안정적인 Streamlit SQL Agent 앱
복잡한 JavaScript와 CSS를 제거하고 기본 Streamlit 컴포넌트만 사용
"""
import streamlit as st
import requests
import json
import os
import uuid
from typing import Dict, Any, List, Generator

# 기본 페이지 설정
st.set_page_config(
    page_title="PAI SQL Agent",
    page_icon="🔍",
    layout="centered"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# API URL 설정
def get_api_base_url():
    """환경에 따라 적절한 API URL 반환"""
    urls_to_try = [
        "http://app:8000",           # Docker 내부
        "http://localhost:8000",     # 로컬
        "http://127.0.0.1:8000"      # 루프백
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

# API 호출 함수들
def call_agent_api_stream(question: str) -> Generator[Dict[str, Any], None, None]:
    """스트리밍 API 호출"""
    try:
        url = f"{API_BASE_URL}/api/agent/query/stream"
        payload = {
            "question": question,
            "session_id": st.session_state.session_id
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

def call_agent_api(question: str) -> Dict[str, Any]:
    """일반 API 호출"""
    try:
        url = f"{API_BASE_URL}/api/agent/query"
        payload = {
            "question": question,
            "session_id": st.session_state.session_id
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"success": False, "error_message": str(e)}

def check_api_health() -> bool:
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/data/health", timeout=3)
        return response.status_code == 200
    except:
        return False

# ====== UI 시작 ======

# 헤더
st.title("🔍 PAI SQL Agent")
st.markdown("**한국 센서스 통계 데이터 AI 분석 도구**")

# API 상태 표시
if check_api_health():
    st.success(f"🟢 API 서버 연결됨")
else:
    st.error(f"🔴 API 서버 연결 실패")

# 사이드바
with st.sidebar:
    st.header("📋 사용 가이드")
    
    st.markdown("""
    **인구 통계 질문 예시:**
    - 2023년 서울특별시의 인구는?
    - 경상북도에서 인구가 가장 많은 시군구는?
    - 전국 시도별 평균 연령이 가장 높은 곳은?
    
    **가구/주택 통계:**
    - 서울특별시 구별 1인 가구 비율 순위
    - 전국에서 평균 가구원수가 가장 많은 지역은?
    
    **사업체 통계:**
    - 2023년 경기도의 사업체 수는?
    - 포항시 남구와 북구의 사업체 수 비교
    """)
    
    st.markdown("---")
    
    # 채팅 기록 관리
    if st.button("🗑️ 채팅 기록 삭제"):
        st.session_state.messages = []
        st.success("채팅 기록이 삭제되었습니다.")
        st.rerun()
    
    if st.button("🔄 새 세션 시작"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.success("새 세션이 시작되었습니다.")
        st.rerun()

# 메인 채팅 영역
st.markdown("---")
st.subheader("💬 대화")

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # 도구 정보 표시 (있는 경우)
        if message["role"] == "assistant" and "used_tools" in message:
            if message["used_tools"]:
                with st.expander("🛠️ 사용된 도구"):
                    for i, tool in enumerate(message["used_tools"], 1):
                        tool_name = tool.get("tool_name", "Unknown")
                        success = tool.get("success", False)
                        status = "✅" if success else "❌"
                        st.write(f"{status} {i}. {tool_name}")

# 사용자 입력
if prompt := st.chat_input("센서스 데이터에 대해 질문해보세요..."):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(prompt)
    
    # AI 응답 생성
    with st.chat_message("assistant"):
        response_container = st.empty()
        
        try:
            # 스트리밍 처리
            full_response = ""
            used_tools = []
            error_occurred = False
            
            with st.spinner("답변을 생성하는 중..."):
                for chunk in call_agent_api_stream(prompt):
                    if chunk.get("type") == "token":
                        full_response += chunk["content"]
                        response_container.write(full_response + "▌")
                    
                    elif chunk.get("type") == "tool_execution":
                        tool_info = chunk["content"]
                        tool_name = tool_info.get("tool_name", "Unknown")
                        st.info(f"🛠️ 도구 실행 중: {tool_name}")
                    
                    elif chunk.get("type") == "final_state":
                        final_state = json.loads(chunk["content"]) if isinstance(chunk["content"], str) else chunk["content"]
                        used_tools = final_state.get("used_tools", [])
                    
                    elif chunk.get("type") == "error":
                        st.error(f"오류: {chunk['content']}")
                        error_occurred = True
                        break
            
            # 최종 응답 표시
            if not error_occurred and full_response:
                response_container.write(full_response)
                
                # 메시지 저장
                assistant_message = {
                    "role": "assistant",
                    "content": full_response,
                    "used_tools": used_tools
                }
                st.session_state.messages.append(assistant_message)
                
                # 도구 정보 표시
                if used_tools:
                    with st.expander("🛠️ 사용된 도구"):
                        for i, tool in enumerate(used_tools, 1):
                            tool_name = tool.get("tool_name", "Unknown")
                            success = tool.get("success", False)
                            status = "✅" if success else "❌"
                            st.write(f"{status} {i}. {tool_name}")
            
            elif not full_response and not error_occurred:
                # 스트리밍 실패시 일반 API 시도
                st.info("스트리밍 연결 실패, 일반 API로 재시도...")
                response = call_agent_api(prompt)
                
                if response.get("success"):
                    content = response.get("message", "응답을 받았습니다.")
                    response_container.write(content)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                        "used_tools": response.get("used_tools", [])
                    })
                else:
                    error_msg = response.get("error_message", "알 수 없는 오류")
                    response_container.error(f"오류: {error_msg}")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"죄송합니다. 오류가 발생했습니다: {error_msg}",
                        "used_tools": []
                    })
        
        except Exception as e:
            response_container.error(f"예상치 못한 오류: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"죄송합니다. 예상치 못한 오류가 발생했습니다: {str(e)}",
                "used_tools": []
            })

# 푸터
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "PAI SQL Agent v1.0.0 | LangGraph + PostgreSQL + SGIS API"
    "</div>",
    unsafe_allow_html=True
)