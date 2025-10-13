"""
Tavily 검색 도구 모듈

LangChain의 TavilySearch를 사용하여 공공기관 정보 검색에 특화된 도구를 제공합니다.
"""

import os
from typing import Dict, Any, List, Optional
from langchain_tavily import TavilySearch


class TavilySearchTool:
    """
    Tavily API를 활용한 웹 검색 도구
    한국 정부기관(*.go.kr)과 공공기관(*.or.kr) 사이트 우선 검색
    """
    
    def __init__(
        self,
        max_results: int = 5,
        topic: str = "general",
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ):
        """
        Tavily 검색 도구 초기화
        
        Args:
            max_results: 반환할 최대 검색 결과 수
            topic: 검색 카테고리 ('general', 'news', 'finance')
            include_answer: LLM 생성 답변 포함 여부
            include_raw_content: 원본 HTML 콘텐츠 포함 여부
            include_images: 이미지 검색 결과 포함 여부
            search_depth: 검색 깊이 ('basic' 또는 'advanced')
            include_domains: 포함할 도메인 리스트
            exclude_domains: 제외할 도메인 리스트
        """
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        # 설정 저장 (모니터링용)
        self.max_results = max_results
        self.search_depth = search_depth
        self.include_domains = include_domains or ["*.go.kr", "*.or.kr"]
        self.exclude_domains = exclude_domains or []
        
        # LangChain TavilySearch 생성
        self.search_tool = TavilySearch(
            max_results=self.max_results,
            topic=topic,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            search_depth=self.search_depth,
            include_domains=self.include_domains,
            exclude_domains=self.exclude_domains if self.exclude_domains else None,
        )
    
    def get_tool_for_agent(self):
        """
        LangGraph 에이전트에서 사용할 수 있는 도구 반환
        """
        return self.search_tool
    
    def get_current_settings(self) -> Dict[str, Any]:
        """
        현재 적용된 설정 반환 (모니터링용)
        """
        return {
            "max_results": self.max_results,
            "search_depth": self.search_depth,
            "include_domains": self.include_domains,
            "exclude_domains": self.exclude_domains,
        }


def create_tavily_tool(
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> TavilySearchTool:
    """
    Tavily 검색 도구 인스턴스 생성 팩토리 함수
    
    Args:
        max_results: 반환할 최대 검색 결과 수
        search_depth: 검색 깊이 ('basic' 또는 'advanced')
        include_domains: 포함할 도메인 리스트
        exclude_domains: 제외할 도메인 리스트
    """
    return TavilySearchTool(
        max_results=max_results,
        topic="general",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
        search_depth=search_depth,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
    )