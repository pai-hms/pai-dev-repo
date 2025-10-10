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
        """
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        # 공공기관 도메인 고정으로 LangChain TavilySearch 생성
        self.search_tool = TavilySearch(
            max_results=max_results,
            topic=topic,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            search_depth=search_depth,
            include_domains=["*.go.kr", "*.or.kr"],  # 공공기관 도메인 고정
        )
    
    def get_tool_for_agent(self):
        """
        LangGraph 에이전트에서 사용할 수 있는 도구 반환
        """
        return self.search_tool


def create_tavily_tool() -> TavilySearchTool:
    """
    Tavily 검색 도구 인스턴스 생성 팩토리 함수
    """
    return TavilySearchTool(
        max_results=5,
        topic="general",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
        search_depth="basic"
    )