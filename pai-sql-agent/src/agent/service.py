"""
통합 AI Agent 서비스 (Supervisor 패턴)
SQL 분석과 일반 대화를 통합 처리하는 단일 진입점

설계 원칙:
- Supervisor-Worker 패턴: 요청을 분류하고 적절한 Worker에게 위임
- 단일 책임 원칙: 요청 라우팅과 조율만 담당
- 의존성 주입: 필요한 서비스들을 외부에서 주입받음
- 계층형 아키텍처: 외부 참조의 유일한 관문 역할
"""
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from .graph import create_sql_agent_graph, get_checkpointer
from .nodes import create_initial_state, create_react_initial_state
from .container import get_container
from .streaming_service import StreamingService
from src.session.container import get_session_service

logger = logging.getLogger(__name__)


class UnifiedAgentService:
    """
    통합 AI Agent 서비스 (Supervisor 패턴)
    
    역할:
    - 요청 분류 및 라우팅 (Supervisor)
    - 적절한 Worker 서비스에게 작업 위임
    - 외부 세계와의 유일한 접점 (Façade)
    
    Worker 서비스들:
    - StreamingService: 실시간 스트리밍 전담
    - SQLAgentGraph: SQL 분석 전담
    - GeneralConversation: 일반 대화 전담
    """
    
    _instance: Optional['UnifiedAgentService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        if UnifiedAgentService._instance is not None:
            raise RuntimeError("UnifiedAgentService는 싱글톤입니다. get_instance()를 사용하세요.")
        
        # Core dependencies (의존성 주입)
        self._agent_graph = None
        self._container = None
        self._session_service = None
        
        # Worker services (전문 작업자들)
        self._streaming_service = None
        
        self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'UnifiedAgentService':
        """싱글톤 인스턴스 가져오기"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance
    
    async def _initialize(self):
        """
        Supervisor 서비스 초기화
        모든 Worker 서비스들을 의존성 주입으로 초기화
        """
        if self._initialized:
            return
            
        logger.info("🚀 Supervisor Agent 서비스 초기화 시작")
        
        try:
            # 1. 핵심 의존성 초기화 (DI 컨테이너)
            self._container = await get_container()
            self._session_service = await get_session_service()
            self._agent_graph = await create_sql_agent_graph()
            
            # 2. Worker 서비스들 초기화 (의존성 주입)
            from .streaming_service import SimpleTokenStreamingService
            self._streaming_service = SimpleTokenStreamingService(
                agent_graph=self._agent_graph,
                session_service=self._session_service
            )
            
            self._initialized = True
            logger.info("✅ Supervisor Agent 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ Supervisor 서비스 초기화 실패: {e}")
            raise
    
    async def query_stream(
        self, 
        question: str, 
        thread_id: Optional[str] = None, 
        session_id: Optional[str] = None,
        stream_mode: str = "messages"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🌊 실시간 스트리밍 요청 처리 (Supervisor 패턴)
        
        역할: 스트리밍 요청을 StreamingService Worker에게 위임
        
        Args:
            question: 사용자 질문
            thread_id: 대화 스레드 ID
            session_id: 세션 ID (하위 호환성)
            stream_mode: 스트리밍 모드 ("messages", "updates", "values", "all")
        
        Yields:
            실시간 스트리밍 데이터
        """
        logger.info(f"🎯 Supervisor: 스트리밍 요청 수신 (mode: {stream_mode})")
        
        try:
            # Worker에게 작업 위임 (실제 토큰 스트리밍)
            async for stream_chunk in self._streaming_service.stream_llm_tokens(
                user_input=question,
                thread_id=thread_id,
                session_id=session_id
            ):
                yield stream_chunk
                
        except Exception as e:
            logger.error(f"❌ Supervisor: 스트리밍 위임 실패: {e}")
            yield {
                "type": "error",
                "content": f"❌ Supervisor 오류: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_request(
        self, 
        user_input: str, 
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🎯 통합 요청 처리 함수 (Supervisor 패턴)
        일반 대화와 SQL 분석을 자동으로 분류하여 처리
        
        Args:
            user_input: 사용자 입력
            thread_id: 대화 스레드 ID
            session_id: 세션 ID (하위 호환성)
            request_type: 강제 요청 타입 ("sql", "general", None=자동분류)
        
        Returns:
            표준화된 응답 형식
        """
        start_time = datetime.now()
        thread_id = thread_id or session_id or f"unified_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"🎯 Supervisor: 요청 처리 시작 (thread_id: {thread_id}): {user_input[:50]}...")
            
            # 세션 관리
            session = await self._session_service.get_or_create_session(
                thread_id=thread_id,
                title=user_input[:50],
                user_id=None
            )
            
            await self._session_service.update_session_activity(
                session.session_id,
                increment_message=True
            )
            
            # 요청 타입 분류 (강제 지정되지 않은 경우)
            if not request_type:
                request_type = await self._classify_request_type(user_input)
            
            # 멀티턴 대화 설정
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            # 요청 타입에 따른 처리 (Worker에게 위임)
            if request_type == "sql":
                # SQL 분석 처리
                result = await self._process_sql_request(user_input, config)
            else:
                # 일반 대화 처리
                result = await self._process_general_request(user_input, config)
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 응답 포맷팅
            response = self._format_unified_response(result, processing_time, thread_id, request_type)
            
            logger.info(f"✅ Supervisor: 요청 처리 완료 ({processing_time:.2f}초)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Supervisor: 요청 처리 실패: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": False,
                "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}",
                "sql_queries": [],
                "results": [],
                "used_tools": [],
                "thread_id": thread_id,
                "session_id": thread_id,
                "processing_time": processing_time,
                "error_message": str(e),
                "request_type": "error"
            }
    
    async def process_request_stream(
        self,
        user_input: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stream_mode: str = "messages",
        request_type: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🌊 통합 스트리밍 요청 처리 (Supervisor 패턴)
        모든 LangGraph 스트리밍 모드 지원
        """
        start_time = datetime.now()
        thread_id = thread_id or session_id or f"unified_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"🌊 Supervisor: 스트리밍 시작 (mode: {stream_mode}, thread_id: {thread_id})")
            
            # 세션 관리
            session = await self._session_service.get_or_create_session(
                thread_id=thread_id,
                title=user_input[:50],
                user_id=None
            )
            
            # 요청 타입 분류
            if not request_type:
                request_type = await self._classify_request_type(user_input)
                
            # 분류 결과 전송
            yield {
                "type": "classification",
                "content": f"🔍 요청 분류: {request_type}",
                "request_type": request_type,
                "timestamp": datetime.now().isoformat()
            }
            
            # 스트리밍 처리 (Worker에게 위임)
            async for chunk in self.query_stream(
                question=user_input,
                thread_id=thread_id,
                stream_mode=stream_mode
            ):
                # 요청 타입 정보 추가
                chunk["request_type"] = request_type
                yield chunk
                
        except Exception as e:
            logger.error(f"❌ Supervisor: 스트리밍 실패: {e}")
            yield {
                "type": "error",
                "content": f"❌ 오류: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _classify_request_type(self, user_input: str) -> str:
        """
        🔍 요청 타입 자동 분류
        SQL 관련 키워드와 패턴을 분석하여 분류
        """
        # 간단한 키워드 기반 분류 (추후 LLM 기반으로 개선 가능)
        sql_keywords = [
            "인구", "가구", "사업체", "통계", "데이터", "조회", "검색", 
            "몇", "얼마", "비교", "순위", "많은", "적은", "평균", "총",
            "시도", "시군구", "지역", "서울", "경기", "부산", "대구",
            "2023", "2022", "2021", "년도"
        ]
        
        user_input_lower = user_input.lower()
        
        # SQL 키워드 매칭 점수 계산
        sql_score = sum(1 for keyword in sql_keywords if keyword in user_input_lower)
        
        # 질문 패턴 분석
        question_patterns = ["?", "얼마", "몇", "어디", "언제", "무엇", "어떤"]
        has_question = any(pattern in user_input_lower for pattern in question_patterns)
        
        # 분류 로직
        if sql_score >= 2 or (sql_score >= 1 and has_question):
            return "sql"
        else:
            return "general"
    
    async def _process_sql_request(self, user_input: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """SQL 요청 처리 (Worker에게 위임)"""
        input_data = create_react_initial_state(user_input, config["configurable"]["thread_id"])
        result = await self._agent_graph.ainvoke(input_data, config=config)
        return result
    
    async def _process_general_request(self, user_input: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """일반 대화 요청 처리"""
        # 일반 대화용 간단한 응답 생성
        from src.llm.service import get_llm_service
        
        try:
            llm_service = await get_llm_service()
            llm = llm_service.llm  # get_model() 대신 llm 프로퍼티 사용
            
            # 간단한 대화 프롬프트
            from langchain_core.prompts import ChatPromptTemplate
            
            prompt = ChatPromptTemplate.from_template(
                "다음 사용자의 질문에 친근하고 도움이 되는 답변을 해주세요:\n\n{user_input}"
            )
            
            chain = prompt | llm
            result = await chain.ainvoke({"user_input": user_input})
            
            return {
                "final_response": result.content,
                "is_complete": True,
                "used_tools": [],
                "final_sql": None,
                "final_result": None
            }
            
        except Exception as e:
            logger.error(f"일반 대화 처리 오류: {e}")
            return {
                "final_response": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "is_complete": False,
                "used_tools": [],
                "final_sql": None,
                "final_result": None
            }
    
    def _format_unified_response(
        self, 
        result: Dict[str, Any], 
        processing_time: float, 
        thread_id: str,
        request_type: str
    ) -> Dict[str, Any]:
        """통합 응답 포맷팅"""
        success = result.get("is_complete", False)
        
        # SQL 쿼리 추출
        sql_queries = []
        if result.get("final_sql"):
            sql_queries.append(result["final_sql"])
        
        # 실행 결과 추출
        results = []
        if result.get("final_result"):
            results.append(result["final_result"])
        
        # 도구 사용 정보 표준화
        used_tools = []
        for tool in result.get("used_tools", []):
            used_tools.append({
                "tool_name": tool.get("tool_name", "unknown"),
                "tool_function": tool.get("tool_name", "unknown"),
                "tool_description": "통합 에이전트 도구",
                "arguments": {"query": result.get("final_sql", "")},
                "execution_order": 1,
                "success": tool.get("success", False),
                "result_preview": tool.get("result_preview", ""),
                "error_message": None
            })
        
        return {
            "success": success,
            "message": result.get("final_response", "처리 완료"),
            "sql_queries": sql_queries,
            "results": results,
            "used_tools": used_tools,
            "thread_id": thread_id,
            "session_id": thread_id,  # 하위 호환성
            "processing_time": processing_time,
            "error_message": None,
            "request_type": request_type,
            "react_iterations": result.get("iteration_count", 0),
            "reasoning_history": result.get("reasoning_history", [])
        }


# ===== 전역 접근 함수 =====

async def get_unified_agent_service() -> UnifiedAgentService:
    """통합 AI Agent 서비스 인스턴스 가져오기"""
    return await UnifiedAgentService.get_instance()

# 하위 호환성을 위한 별칭들
async def get_sql_agent_service() -> UnifiedAgentService:
    """SQL Agent 서비스 인스턴스 가져오기 (하위 호환성)"""
    return await UnifiedAgentService.get_instance()

async def get_main_agent_service() -> UnifiedAgentService:
    """메인 Agent 서비스 인스턴스 가져오기 (하위 호환성)"""
    return await UnifiedAgentService.get_instance()


# ===== 호환성 함수 (기존 코드와의 호환성) =====

def get_sql_agent_service_sync(enable_checkpointer: bool = True) -> 'UnifiedAgentServiceWrapper':
    """기존 동기 방식 호환성을 위한 래퍼"""
    return UnifiedAgentServiceWrapper()


class UnifiedAgentServiceWrapper:
    """기존 인터페이스 호환성을 위한 래퍼 클래스"""
    
    async def invoke_query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """기존 invoke_query 메서드 호환성"""
        service = await get_unified_agent_service()
        return await service.process_request(question, session_id=session_id)
    
    async def query(self, question: str, thread_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """기존 query 메서드 호환성"""
        service = await get_unified_agent_service()
        return await service.process_request(question, thread_id, session_id)
    
    def get_sql_agent_service(self):
        """기존 get_sql_agent_service 메서드 호환성"""
        return self
