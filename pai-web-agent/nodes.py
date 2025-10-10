"""
LangGraph 노드 정의 모듈

공공기관 정보 검색에 특화된 커스텀 노드들을 정의합니다.
각 노드는 특정 기능을 담당하며, 상태를 통해 데이터를 주고받습니다.
"""

import json
from typing import Dict, Any, List, Optional, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tools import create_tavily_tool
from prompts import get_system_prompt, get_enhanced_query


class AgentState:
    """
    에이전트 상태 클래스
    
    LangGraph에서 노드 간 데이터 전달을 위한 상태 관리
    """
    
    def __init__(self):
        # 기본 상태 필드들
        self.messages: List[Dict[str, Any]] = []
        self.current_query: str = ""
        self.enhanced_query: str = ""
        self.search_results: Optional[Dict[str, Any]] = None
        self.analysis_result: Optional[Dict[str, Any]] = None
        self.final_response: str = ""
        self.error: Optional[str] = None
        
        # 설정 관련
        self.prompt_type: str = "default"
        self.search_settings: Dict[str, Any] = {}
        
        # 메타데이터
        self.step_count: int = 0
        self.processing_time: float = 0.0
        
        # 라우팅 결정
        self.next_action: Literal["search", "respond", "analyze", "end"] = "search"
        self.needs_search: bool = True
        self.confidence_score: float = 0.0


class QueryAnalysisNode:
    """
    쿼리 분석 노드
    
    사용자 질문을 분석하여 검색이 필요한지, 어떤 타입의 정보가 필요한지 판단
    """
    
    def __init__(self, llm: ChatOpenAI, prompt_type: str = "default"):
        self.llm = llm
        self.prompt_type = prompt_type
        
    def __call__(self, state: AgentState) -> AgentState:
        """
        쿼리 분석 실행
        
        Args:
            state: 현재 에이전트 상태
            
        Returns:
            업데이트된 상태
        """
        try:
            state.step_count += 1
            
            # 현재 쿼리 추출
            if state.messages:
                last_message = state.messages[-1]
                if last_message.get("role") == "user":
                    state.current_query = last_message.get("content", "")
            
            if not state.current_query:
                state.error = "분석할 쿼리가 없습니다."
                state.next_action = "end"
                return state
            
            # 쿼리 향상
            state.enhanced_query = get_enhanced_query(
                state.current_query, 
                state.search_settings.get("include_domains", [])
            )
            
            # 쿼리 분석을 위한 프롬프트
            analysis_prompt = f"""
            다음 사용자 질문을 분석하여 JSON 형태로 응답하세요:
            
            질문: {state.current_query}
            
            분석 결과를 다음 형식으로 제공하세요:
            {{
                "needs_search": true/false,
                "query_type": "factual/current_events/statistics/policy/general",
                "confidence": 0.0-1.0,
                "reasoning": "분석 이유",
                "suggested_domains": ["domain1", "domain2"]
            }}
            
            판단 기준:
            1. 최신 정보, 통계, 정책이 필요하면 needs_search: true
            2. 일반적인 지식으로 답변 가능하면 needs_search: false
            3. 공공기관 관련 질문이면 suggested_domains에 관련 도메인 추가
            """
            
            # LLM을 통한 분석
            messages = [
                SystemMessage(content=get_system_prompt(self.prompt_type)),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # JSON 파싱 시도
            try:
                analysis_result = json.loads(response.content)
                state.analysis_result = analysis_result
                
                # 다음 액션 결정
                if analysis_result.get("needs_search", True):
                    state.next_action = "search"
                    state.needs_search = True
                else:
                    state.next_action = "respond"
                    state.needs_search = False
                
                state.confidence_score = analysis_result.get("confidence", 0.5)
                
                # 도메인 제안이 있으면 검색 설정에 추가
                suggested_domains = analysis_result.get("suggested_domains", [])
                if suggested_domains and not state.search_settings.get("include_domains"):
                    state.search_settings["include_domains"] = suggested_domains
                
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 설정
                state.analysis_result = {
                    "needs_search": True,
                    "query_type": "general",
                    "confidence": 0.5,
                    "reasoning": "JSON 파싱 실패로 기본 검색 수행"
                }
                state.next_action = "search"
                state.needs_search = True
                state.confidence_score = 0.5
            
        except Exception as e:
            state.error = f"쿼리 분석 중 오류: {str(e)}"
            state.next_action = "end"
        
        return state


class SearchNode:
    """
    검색 노드
    
    Tavily API를 사용하여 웹 검색을 수행하고 결과를 상태에 저장
    """
    
    def __init__(self):
        self.tavily_tool = create_tavily_tool()
        
    def __call__(self, state: AgentState) -> AgentState:
        """
        검색 실행
        
        Args:
            state: 현재 에이전트 상태
            
        Returns:
            업데이트된 상태
        """
        try:
            state.step_count += 1
            
            if not state.needs_search:
                state.next_action = "respond"
                return state
            
            # 검색 쿼리 결정 (향상된 쿼리 우선 사용)
            search_query = state.enhanced_query or state.current_query
            
            if not search_query:
                state.error = "검색할 쿼리가 없습니다."
                state.next_action = "end"
                return state
            
            # 검색 설정 적용
            search_params = {
                "query": search_query,
                "max_results": state.search_settings.get("max_results", 5),
                "search_depth": state.search_settings.get("search_depth", "basic")
            }
            
            # 도메인 필터링 적용
            include_domains = state.search_settings.get("include_domains")
            exclude_domains = state.search_settings.get("exclude_domains")
            
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            
            # 검색 실행
            search_result = self.tavily_tool.search(**search_params)
            
            if search_result["success"]:
                state.search_results = search_result["data"]
                state.next_action = "respond"
            else:
                state.error = f"검색 실패: {search_result['error']}"
                state.next_action = "respond"  # 검색 실패해도 응답 시도
                
        except Exception as e:
            state.error = f"검색 중 오류: {str(e)}"
            state.next_action = "respond"  # 오류 발생해도 응답 시도
        
        return state


class ResponseGenerationNode:
    """
    응답 생성 노드
    
    검색 결과를 바탕으로 최종 사용자 응답을 생성
    """
    
    def __init__(self, llm: ChatOpenAI, prompt_type: str = "default"):
        self.llm = llm
        self.prompt_type = prompt_type
        
    def __call__(self, state: AgentState) -> AgentState:
        """
        응답 생성 실행
        
        Args:
            state: 현재 에이전트 상태
            
        Returns:
            업데이트된 상태
        """
        try:
            state.step_count += 1
            
            # 시스템 프롬프트 가져오기
            system_prompt = get_system_prompt(self.prompt_type)
            
            # 응답 생성을 위한 컨텍스트 구성
            context_parts = [f"사용자 질문: {state.current_query}"]
            
            # 분석 결과 추가
            if state.analysis_result:
                analysis = state.analysis_result
                context_parts.append(f"질문 유형: {analysis.get('query_type', 'general')}")
                context_parts.append(f"분석 신뢰도: {analysis.get('confidence', 0.5):.2f}")
            
            # 검색 결과 추가
            if state.search_results:
                context_parts.append("검색 결과:")
                if isinstance(state.search_results, dict):
                    # 검색 결과를 읽기 쉽게 포맷팅
                    results = state.search_results.get("results", [])
                    for i, result in enumerate(results[:3], 1):  # 상위 3개만 사용
                        context_parts.append(f"{i}. {result.get('title', 'N/A')}")
                        context_parts.append(f"   출처: {result.get('url', 'N/A')}")
                        context_parts.append(f"   내용: {result.get('content', 'N/A')[:200]}...")
                else:
                    context_parts.append(str(state.search_results)[:500] + "...")
            
            # 오류 정보 추가
            if state.error:
                context_parts.append(f"처리 중 발생한 오류: {state.error}")
                context_parts.append("오류가 있었지만 가능한 범위에서 답변을 제공합니다.")
            
            # 도메인 필터링 정보 추가
            if state.search_settings.get("include_domains"):
                domains = state.search_settings["include_domains"]
                context_parts.append(f"검색 대상 도메인: {', '.join(domains[:3])}")
            
            context = "\n".join(context_parts)
            
            # 응답 생성 프롬프트
            response_prompt = f"""
            다음 정보를 바탕으로 사용자에게 도움이 되는 답변을 생성하세요:
            
            {context}
            
            답변 지침:
            1. 검색 결과가 있으면 이를 바탕으로 정확한 정보 제공
            2. 출처를 명확히 밝히고 최신 정보임을 확인
            3. 구조화된 형태로 읽기 쉽게 작성
            4. 관련 공공기관이나 추가 정보 확인 방법 안내
            5. 오류가 있었다면 한계를 명시하되 가능한 도움 제공
            
            사용자 친화적이고 신뢰할 수 있는 답변을 작성해주세요.
            """
            
            # LLM을 통한 응답 생성
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=response_prompt)
            ]
            
            response = self.llm.invoke(messages)
            state.final_response = response.content
            
            # 응답을 메시지 히스토리에 추가
            state.messages.append({
                "role": "assistant",
                "content": state.final_response,
                "metadata": {
                    "step_count": state.step_count,
                    "confidence": state.confidence_score,
                    "used_search": state.search_results is not None,
                    "error": state.error
                }
            })
            
            state.next_action = "end"
            
        except Exception as e:
            error_msg = f"응답 생성 중 오류: {str(e)}"
            state.error = error_msg
            state.final_response = f"죄송합니다. {error_msg} 다시 시도해주세요."
            state.next_action = "end"
        
        return state


class RouterNode:
    """
    라우터 노드
    
    현재 상태를 바탕으로 다음에 실행할 노드를 결정
    """
    
    def __call__(self, state: AgentState) -> str:
        """
        다음 노드 결정
        
        Args:
            state: 현재 에이전트 상태
            
        Returns:
            다음 실행할 노드 이름
        """
        if state.error and state.next_action == "end":
            return "end"
        
        if state.next_action == "search":
            return "search"
        elif state.next_action == "respond":
            return "response"
        elif state.next_action == "analyze":
            return "analysis"
        else:
            return "end"


# 노드 팩토리 함수들
def create_analysis_node(llm: ChatOpenAI, prompt_type: str = "default") -> QueryAnalysisNode:
    """쿼리 분석 노드 생성"""
    return QueryAnalysisNode(llm, prompt_type)


def create_search_node() -> SearchNode:
    """검색 노드 생성"""
    return SearchNode()


def create_response_node(llm: ChatOpenAI, prompt_type: str = "default") -> ResponseGenerationNode:
    """응답 생성 노드 생성"""
    return ResponseGenerationNode(llm, prompt_type)


def create_router_node() -> RouterNode:
    """라우터 노드 생성"""
    return RouterNode()
