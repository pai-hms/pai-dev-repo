"""
LangGraph 그래프 정의 모듈

간단한 React 패턴으로 에이전트가 스스로 도구 사용을 판단합니다.
"""

import time
from typing import Dict, Any, List, Optional
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tools import create_tavily_tool
from prompts import get_system_prompt


class SimpleReactGraph:
    """
    간단한 React 패턴 그래프
    
    에이전트가 스스로 도구 사용을 판단하고 실행
    """
    
    def __init__(self, llm: ChatOpenAI, search_settings: Optional[Dict[str, Any]] = None):
        """
        그래프 초기화
        
        Args:
            llm: OpenAI LLM 인스턴스
            search_settings: Tavily 검색 설정
        """
        self.llm = llm
        self.search_settings = search_settings or {}
        
        # 검색 설정에서 Tavily 파라미터 추출
        max_results = self.search_settings.get("max_results", 5)
        search_depth = self.search_settings.get("search_depth", "basic")
        include_domains = self.search_settings.get("include_domains", None)
        exclude_domains = self.search_settings.get("exclude_domains", None)
        
        # 도구 생성 (설정 반영)
        self.tavily_tool = create_tavily_tool(
            max_results=max_results,
            search_depth=search_depth,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        tools = [self.tavily_tool.get_tool_for_agent()]
        
        # React 에이전트 생성 (메모리 없음)
        self.graph = create_react_agent(
            model=llm,
            tools=tools
        )
    
    async def invoke(self, query: str, search_settings: Optional[Dict[str, Any]] = None, 
                    thread_id: str = "default") -> Dict[str, Any]:
        """
        비동기 실행 (React 패턴)
        """
        try:
            # 시스템 프롬프트와 사용자 질문으로 메시지 구성
            messages = [
                SystemMessage(content=get_system_prompt()),
                HumanMessage(content=query)
            ]
            
            # React 에이전트 비동기 실행
            result = await self.graph.ainvoke({"messages": messages})
            
            # 마지막 AI 메시지 추출
            final_response = ""
            if result.get("messages"):
                for msg in reversed(result["messages"]):
                    if isinstance(msg, AIMessage):
                        final_response = msg.content
                        break
            
            return {
                "success": True,
                "response": final_response or "응답을 생성할 수 없습니다.",
                "metadata": {
                    "message_count": len(result.get("messages", [])),
                    "used_tools": any("tool_calls" in str(msg) for msg in result.get("messages", []))
                },
                "messages": result.get("messages", []),
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": None,
                "metadata": {},
                "messages": [],
                "error": str(e)
            }
    
    def stream(self, query: str, search_settings: Optional[Dict[str, Any]] = None,
              thread_id: str = "default", stream_mode: str = "messages"):
        """
        스트리밍 실행 (React 패턴)
        
        Args:
            query: 사용자 질문
            search_settings: 검색 설정 (사용 안함)
            thread_id: 스레드 ID (사용 안함)
            stream_mode: 스트리밍 모드
            
        Yields:
            실행 단계별 결과
        """
        try:
            # 시스템 프롬프트와 사용자 질문으로 메시지 구성
            messages = [
                SystemMessage(content=get_system_prompt()),
                HumanMessage(content=query)
            ]
            
            # React 에이전트 스트리밍 실행
            for step in self.graph.stream({"messages": messages}, stream_mode=stream_mode):
                yield step
                
        except Exception as e:
            yield {"error": str(e)}
    


def create_public_info_graph(llm: ChatOpenAI, search_settings: Optional[Dict[str, Any]] = None) -> SimpleReactGraph:
    """
    공공기관 정보 검색 그래프 생성 팩토리 함수
    
    Args:
        llm: OpenAI LLM 인스턴스
        search_settings: Tavily 검색 설정 (max_results, search_depth, include_domains, exclude_domains)
        
    Returns:
        SimpleReactGraph 인스턴스
    """
    return SimpleReactGraph(llm, search_settings)