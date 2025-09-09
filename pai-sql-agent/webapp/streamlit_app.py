import streamlit as st
import requests
import json
import time
import os
from typing import Dict, Any, List

# 페이지 설정
st.set_page_config(
    page_title="PAI SQL Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .stChat {
        max-height: 600px;
        overflow-y: auto;
    }
    .sql-result {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f44336;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# API 베이스 URL - 환경에 따라 동적 결정
def get_api_base_url():
    """환경에 따라 적절한 API URL 반환"""
    # Docker 환경인지 확인
    if os.path.exists('/.dockerenv'):
        # Docker 컨테이너 내부에서 실행 중
        return "http://app:8000"
    else:
        # 로컬 환경에서 실행 중
        return "http://localhost:8000"

API_BASE_URL = get_api_base_url()

# API 연결 테스트 및 fallback
def test_and_get_api_url():
    """API 연결 테스트 후 작동하는 URL 반환"""
    urls_to_try = [
        "http://app:8000",           # Docker 내부 네트워크
        "http://localhost:8000",     # 로컬 호스트
        "http://127.0.0.1:8000",     # 루프백
        "http://host.docker.internal:8000"  # Docker Desktop의 경우
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(f"{url}/", timeout=3)
            if response.status_code == 200:
                return url
        except:
            continue
    
    return "http://localhost:8000"  # 기본값

# 실제 사용할 API URL
API_BASE_URL = test_and_get_api_url()


def call_agent_api(question: str, stream: bool = False) -> Dict[str, Any]:
    """Agent API 호출"""
    try:
        url = f"{API_BASE_URL}/api/agent/query"
        if stream:
            url += "/stream"
        
        payload = {
            "question": question,
            "session_id": st.session_state.session_id,
            "stream": stream
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        if stream:
            return {"stream": response}
        else:
            return response.json()
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error_message": f"API 호출 실패: {str(e)}"
        }


def get_tables() -> List[str]:
    """테이블 목록 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/data/tables", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return []


def get_table_info(table_name: str) -> Dict[str, Any]:
    """테이블 정보 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/data/tables/{table_name}", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {}


def search_admin_area(search_term: str) -> List[Dict[str, str]]:
    """행정구역 검색"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/data/search/admin-area",
            json={"search_term": search_term},
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except:
        return []


# 메인 UI
st.title("🔍 PAI SQL Agent")
st.subheader("한국 센서스 통계 데이터 AI 분석 도구")

# 사이드바
with st.sidebar:
    st.header("📊 데이터 정보")
    
    # 연결 상태 확인
    st.write(f"**API 서버:** `{API_BASE_URL}`")
    try:
        health_response = requests.get(f"{API_BASE_URL}/api/data/health", timeout=5)
        if health_response.status_code == 200:
            st.success("🟢 API 서버 연결됨")
        else:
            st.error("🔴 API 서버 응답 오류")
    except Exception as e:
        st.error(f"🔴 API 서버에 연결할 수 없습니다: {str(e)}")
    
    # 테이블 목록
    with st.expander("테이블 목록", expanded=True):
        tables = get_tables()
        if tables:
            for table in tables:
                if st.button(f"📋 {table}", key=f"table_{table}"):
                    table_info = get_table_info(table)
                    if table_info:
                        st.session_state.selected_table = table_info
        else:
            st.warning("테이블을 불러올 수 없습니다.")
    
    # 행정구역 검색
    with st.expander("행정구역 검색"):
        search_term = st.text_input("지역명 입력", placeholder="예: 포항, 서울, 강남구")
        if search_term:
            areas = search_admin_area(search_term)
            if areas:
                st.write("검색 결과:")
                for area in areas[:10]:
                    st.write(f"• {area['adm_nm']} ({area['adm_cd']}) - {area['level']}")
            else:
                st.warning("검색 결과가 없습니다.")
    
    # 도움말
    with st.expander("💡 사용 팁"):
        st.markdown("""
        **인구 통계 질문:**
        - 2023년 서울특별시의 인구는?
        - 경상북도에서 인구가 가장 많은 시군구는?
        - 2020년 대비 2023년 인구 증가율이 높은 지역 상위 10곳
        - 전국 시도별 평균 연령이 가장 높은 곳은?
        
        **가구/주택 통계 질문:**
        - 서울특별시 구별 1인 가구 비율 순위
        - 부산광역시의 아파트 수는?
        - 전국에서 평균 가구원수가 가장 많은 지역은?
        
        **사업체 통계 질문:**
        - 2023년 경기도의 사업체 수는?
        - 종사자 수가 가장 많은 시도는?
        - 포항시 남구와 북구의 사업체 수 비교
        
        **비교 분석 질문:**
        - 수도권(서울/인천/경기) 인구 비교
        - 영남권 주요 도시들의 인구밀도 순위
        - 2015년과 2023년 전국 인구 변화
        
        **지원 데이터:**
        - 인구/가구/주택/사업체 통계 (2015-2023)
        - 농가/임가/어가 통계 (2000, 2005, 2010, 2015, 2020)
        - 시도/시군구/읍면동 단위 데이터
        """)

# 메인 채팅 영역
col1, col2 = st.columns([3, 1])

with col1:
    st.header("💬 질문하기")
    
    # 채팅 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # SQL 결과가 있으면 표시
            if "sql_queries" in message and message["sql_queries"]:
                st.markdown("**실행된 SQL 쿼리:**")
                for i, sql in enumerate(message["sql_queries"], 1):
                    st.code(sql, language="sql")
    
    # 사용자 입력
    if prompt := st.chat_input("센서스 데이터에 대해 질문해보세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하는 중..."):
                response = call_agent_api(prompt)
                
                if response.get("success"):
                    # 성공적인 응답
                    message_content = response.get("message", "응답을 받았습니다.")
                    st.write(message_content)
                    
                    # SQL 쿼리 표시
                    sql_queries = response.get("sql_queries", [])
                    if sql_queries:
                        st.markdown("**실행된 SQL 쿼리:**")
                        for i, sql in enumerate(sql_queries, 1):
                            st.code(sql, language="sql")
                    
                    # 처리 시간 표시
                    processing_time = response.get("processing_time")
                    if processing_time:
                        st.caption(f"처리 시간: {processing_time:.2f}초")
                    
                    # 메시지 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": message_content,
                        "sql_queries": sql_queries,
                        "processing_time": processing_time
                    })
                    
                else:
                    # 에러 응답
                    error_msg = response.get("error_message", "알 수 없는 오류가 발생했습니다.")
                    st.error(f"오류: {error_msg}")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"죄송합니다. 오류가 발생했습니다: {error_msg}"
                    })

with col2:
    st.header("⚙️ 설정")
    
    # 채팅 히스토리 관리
    if st.button("🗑️ 채팅 기록 삭제"):
        st.session_state.messages = []
        st.success("채팅 기록이 삭제되었습니다.")
    
    # 새 세션 시작
    if st.button("🔄 새 세션 시작"):
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.success("새 세션이 시작되었습니다.")
    
    # 시스템 상태
    st.subheader("📡 시스템 상태")
    try:
        health_response = requests.get(f"{API_BASE_URL}/api/data/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            status_color = {
                "healthy": "🟢",
                "degraded": "🟡", 
                "unhealthy": "🔴"
            }.get(health_data.get("status", "unhealthy"), "🔴")
            
            st.write(f"{status_color} 전체 상태: {health_data.get('status', 'unknown')}")
            
            db_status = "🟢 연결됨" if health_data.get("database_connected") else "🔴 연결 실패"
            st.write(f"데이터베이스: {db_status}")
            
            api_status = "🟢 연결됨" if health_data.get("sgis_api_connected") else "🔴 연결 실패"
            st.write(f"SGIS API: {api_status}")
        else:
            st.write("🔴 API 서버에 연결할 수 없습니다.")
    except Exception as e:
        st.write(f"🔴 시스템 상태를 확인할 수 없습니다: {str(e)}")

# 선택된 테이블 정보 표시
if hasattr(st.session_state, 'selected_table'):
    with st.expander(f"📋 {st.session_state.selected_table['table_name']} 테이블 정보", expanded=True):
        table_info = st.session_state.selected_table
        
        st.write(f"**설명:** {table_info.get('description', '설명 없음')}")
        
        st.write("**컬럼 정보:**")
        for col in table_info.get('columns', []):
            nullable = "NULL 허용" if col.get('is_nullable') == 'YES' else "NOT NULL"
            st.write(f"• `{col['column_name']}`: {col['data_type']} ({nullable})")

# 푸터
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "PAI SQL Agent v1.0.0 | LangGraph + PostgreSQL + SGIS API"
    "</div>",
    unsafe_allow_html=True
)