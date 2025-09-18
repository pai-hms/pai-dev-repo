"""
실시간 토큰 스트리밍 Streamlit SQL Agent 앱
LangGraph의 실제 토큰 스트리밍을 활용한 개선된 UI
"""
import streamlit as st
import requests
import json
import os
import uuid
from typing import Dict, Any, List, Generator

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
    """통합 스트리밍 API 호출 - 모든 요청이 자동으로 스트리밍"""
    try:
        url = f"{API_BASE_URL}/api/agent/query"
        payload = {
            "question": question,
            "session_id": st.session_state.session_id,
            "stream_mode": "all"  # 모든 스트리밍 정보 포함
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
    - 경기도에서 인구가 가장 많은 시군구는?
    - 전국 시도별 평균 연령이 가장 높은 곳은?
    
    **가구/주택 통계:**
    - 서울시 구별 1인 가구 비율은?
    - 경기도 평균 가구원수는 얼마인가요?
    
    **사업체 통계:**
    - 2023년 부산시 사업체 수는?
    - 전국에서 사업체가 가장 많은 지역은?
    """)
    
    st.markdown("---")
    st.header("🔄 실시간 스트리밍")
    
    st.info("""
    **자동 통합 스트리밍:**
    • 🟢 **토큰 스트리밍**: 실시간 답변 생성
    • 🔵 **노드 업데이트**: 처리 단계 표시
    • 🟡 **상태 업데이트**: 그래프 상태 변화
    • 🟣 **도구 실행**: SQL 실행 및 분석 과정
    
    모든 요청이 자동으로 최적화된 스트리밍으로 처리됩니다.
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
    
    # 세션 관리
    if st.button("🗑️ 대화 기록 삭제"):
        st.session_state.messages = []
        st.success("대화 기록이 삭제되었습니다.")
        st.rerun()
    
    if st.button("🔄 새 세션 시작"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.success("새 세션이 시작되었습니다.")
        st.rerun()

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
        
        # 스트리밍 정보 표시 (있는 경우)
        if message["role"] == "assistant" and "streaming_info" in message:
            info = message["streaming_info"]
            with st.expander("📊 스트리밍 정보"):
                st.write(f"🟢 토큰 수: {info.get('total_tokens', 0)}")
                st.write(f"🔵 노드 실행: {info.get('nodes_executed', 0)}")
                st.write(f"🟡 상태 업데이트: {info.get('state_updates', 0)}")
                st.write(f"🟣 도구 실행: {info.get('tools_executed', 0)}")
                st.write(f"⏱️ 응답 시간: {info.get('response_time', 0):.2f}초")

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
        status_container = st.empty()
        progress_container = st.empty()
        
        try:
            # 실시간 통합 스트리밍
            full_response = ""
            used_tools = []
            error_occurred = False
            
            # 스트리밍 통계
            streaming_stats = {
                "total_tokens": 0,
                "nodes_executed": 0,
                "state_updates": 0,
                "tools_executed": 0,
                "start_time": None,
                "end_time": None
            }
            
            node_sequence = []
            
            with st.spinner("🤖 AI가 답변을 생성하는 중..."):
                for chunk in call_agent_stream(prompt):
                    chunk_type = chunk.get("type", "unknown")
                    
                    # 시작 시간 기록
                    if streaming_stats["start_time"] is None:
                        streaming_stats["start_time"] = chunk.get("timestamp")
                    
                    if chunk_type == "token":
                        # 실시간 토큰 추가 (타이핑 효과)
                        token_content = chunk.get("content", "")
                        full_response += token_content
                        response_container.write(full_response + "▌")
                        
                        streaming_stats["total_tokens"] += 1
                        
                        # 진행률 표시
                        progress = chunk.get("progress", 0)
                        if progress > 0:
                            progress_container.progress(progress / 100, f"생성 중... {progress:.0f}%")
                    
                    elif chunk_type == "node_update":
                        # 노드 실행 상태 표시
                        node_name = chunk.get("node", "unknown")
                        if node_name not in node_sequence:
                            node_sequence.append(node_name)
                            streaming_stats["nodes_executed"] += 1
                        
                        status_container.info(f"🔄 노드 실행: {' → '.join(node_sequence)}")
                    
                    elif chunk_type == "state_update":
                        # 그래프 상태 업데이트
                        streaming_stats["state_updates"] += 1
                        status_container.info("📊 그래프 상태 업데이트됨")
                    
                    elif chunk_type == "classification":
                        # 요청 분류 결과
                        request_type = chunk.get("request_type", "unknown")
                        status_container.info(f"🔍 요청 분류: {request_type}")
                    
                    elif chunk_type == "tool_start":
                        # 도구 실행 시작
                        status_container.info(chunk.get("content", "🛠️ 도구 실행 중..."))
                    
                    elif chunk_type == "tool_execution":
                        # 도구 실행 정보
                        streaming_stats["tools_executed"] += 1
                        tool_info = chunk.get("content", {})
                        
                        if isinstance(tool_info, dict):
                            tool_name = tool_info.get("tool_name", "Unknown")
                            used_tools.append(tool_info)
                        else:
                            tool_name = str(tool_info)
                        
                        status_container.info(f"🛠️ 도구 실행: {tool_name}")
                    
                    elif chunk_type == "complete" or chunk_type == "done":
                        # 완료 상태
                        streaming_stats["end_time"] = chunk.get("timestamp")
                        status_container.success(chunk.get("content", "✅ 응답 생성 완료"))
                        
                        total_tokens = chunk.get("total_tokens", streaming_stats["total_tokens"])
                        if total_tokens > 0:
                            status_container.info(f"📊 총 {total_tokens}개 토큰 생성됨")
                        break
                    
                    elif chunk_type == "error":
                        st.error(f"오류: {chunk.get('content', 'Unknown error')}")
                        error_occurred = True
                        break
                    
                    elif chunk_type == "progress":
                        # 🎯 진행상황 표시 (새로 추가)
                        progress_content = chunk.get("content", "")
                        status_container.info(progress_content)
                        
                        # 진행상황 통계 업데이트
                        if "SQLAgentNode" in progress_content:
                            streaming_stats["nodes_executed"] += 1
                        elif "도구 호출됨" in progress_content:
                            streaming_stats["tools_executed"] += 1
            
            # 응답 시간 계산
            if streaming_stats["start_time"] and streaming_stats["end_time"]:
                from datetime import datetime
                try:
                    start = datetime.fromisoformat(streaming_stats["start_time"].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(streaming_stats["end_time"].replace('Z', '+00:00'))
                    streaming_stats["response_time"] = (end - start).total_seconds()
                except:
                    streaming_stats["response_time"] = 0
            
            # 최종 응답 표시
            if not error_occurred and full_response:
                response_container.write(full_response)
                status_container.empty()  # 상태 메시지 제거
                progress_container.empty()  # 진행률 제거
                
                # 메시지 저장 (스트리밍 정보 포함)
                assistant_message = {
                    "role": "assistant",
                    "content": full_response,
                    "used_tools": used_tools,
                    "streaming_info": {
                        "total_tokens": streaming_stats["total_tokens"],
                        "nodes_executed": streaming_stats["nodes_executed"],
                        "state_updates": streaming_stats["state_updates"],
                        "tools_executed": streaming_stats["tools_executed"],
                        "response_time": streaming_stats.get("response_time", 0)
                    }
                }
                st.session_state.messages.append(assistant_message)
            
            elif not full_response and not error_occurred:
                # 응답이 없는 경우
                st.warning("응답을 생성하지 못했습니다. 다시 시도해주세요.")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "죄송합니다. 응답을 생성하지 못했습니다. 다시 시도해주세요.",
                    "used_tools": []
                })
        
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
