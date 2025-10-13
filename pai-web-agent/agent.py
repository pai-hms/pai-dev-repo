import os
import asyncio
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

from graph import create_public_info_graph, SimpleReactGraph
from prompts import get_system_prompt

# 환경 변수 로드
load_dotenv()


class SupervisedAgent:
    """
    LangGraph 기반 공공기관 정보 검색 전문 에이전트
    
    커스텀 노드와 그래프 구조를 사용하여:
    1. 쿼리 분석 - 검색 필요성 및 타입 판단
    2. 웹 검색 - Tavily API를 통한 정보 수집
    3. 응답 생성 - 구조화된 최종 답변 제공
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.1, 
                 search_settings: Optional[Dict[str, Any]] = None):
        """
        Supervised Agent 초기화
        
        Args:
            model_name: 사용할 OpenAI 모델명
            temperature: 모델의 창의성 수준 (0.0 ~ 1.0)
            search_settings: Tavily 검색 설정 (옵션)
        """
        # OpenAI API 키 확인
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        # 설정 저장
        self.model_name = model_name
        self.temperature = temperature
        
        # LLM 모델 초기화
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=self.openai_api_key
        )
        
        # 검색 설정 가져오기 (인자로 전달되거나 세션에서 가져오기)
        if search_settings is None:
            search_settings = self._get_search_settings()
        
        # 공공기관 정보 검색 그래프 초기화 (설정 전달)
        self.graph = create_public_info_graph(self.llm, search_settings)
        
        # 시스템 프롬프트 저장 (호환성을 위해)
        self.system_message = get_system_prompt()
    
    def _get_search_settings(self) -> Dict[str, Any]:
        """
        Streamlit 세션에서 검색 설정 가져오기
        
        Returns:
            검색 설정 딕셔너리
        """
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'stream_settings' in st.session_state:
                return st.session_state.stream_settings
        except:
            pass
        
        return {}
    
    async def process_query(self, query: str, thread_id: str = "default") -> Dict[str, Any]:
        """
        비동기 쿼리 처리 (React 패턴)
        
        Args:
            query: 사용자 질문
            thread_id: 대화 스레드 ID
            
        Returns:
            처리 결과를 포함한 딕셔너리
        """
        try:
            # 검색 설정 가져오기
            search_settings = self._get_search_settings()
            
            # 비동기 그래프 실행
            result = await self.graph.invoke(
                query=query,
                search_settings=search_settings,
                thread_id=thread_id
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "response": None,
                "metadata": {},
                "messages": [],
                "error": str(e)
            }
    
    def stream_response(self, query: str, thread_id: str = "default", stream_mode: str = "messages"):
        """
        스트리밍 응답 생성 (그래프 기반)
        
        Args:
            query: 사용자 질문
            thread_id: 대화 스레드 ID
            stream_mode: 스트리밍 모드 (기본값: "messages")
            
        Yields:
            처리 단계별 결과
        """
        try:
            # 검색 설정 가져오기
            search_settings = self._get_search_settings()
            
            # 그래프 스트리밍 실행
            for step in self.graph.stream(
                query=query,
                search_settings=search_settings,
                thread_id=thread_id,
                stream_mode=stream_mode
            ):
                yield step
                
        except Exception as e:
            yield {"error": str(e)}
    
    def stream_response_with_metadata(self, query: str, thread_id: str = "default", stream_mode="messages"):
        """
        메타데이터가 포함된 스트리밍 응답 생성 (그래프 기반)
        
        Args:
            query: 사용자 질문
            thread_id: 대화 스레드 ID
            stream_mode: 스트리밍 모드
            
        Yields:
            메타데이터가 포함된 처리 단계별 결과
        """
        import time
        
        try:
            # 검색 설정 가져오기
            search_settings = self._get_search_settings()
            
            step_count = 0
            start_time = time.time()
            
            # 그래프 스트리밍 실행
            for step in self.graph.stream(
                query=query,
                search_settings=search_settings,
                thread_id=thread_id,
                stream_mode=stream_mode
            ):
                step_count += 1
                current_time = time.time()
                
                # 메타데이터 추가
                enriched_step = {
                    "step_number": step_count,
                    "timestamp": current_time,
                    "elapsed_time": current_time - start_time,
                    "stream_mode": stream_mode,
                    "data": step,
                    "data_size": len(str(step)) if step else 0
                }
                
                yield enriched_step
                
        except Exception as e:
            yield {
                "step_number": -1,
                "timestamp": time.time(),
                "elapsed_time": 0,
                "stream_mode": stream_mode,
                "error": str(e),
                "data": None,
                "data_size": 0
            }
    
    async def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """
        스트리밍 전용 - 대화 기록은 Streamlit 세션에서 관리
        """
        return [{"info": "대화 기록은 Streamlit 세션에서 관리됩니다."}]
    
    async def get_graph_info(self) -> Dict[str, Any]:
        """
        그래프 구조 정보 반환
        
        Returns:
            그래프 정보 딕셔너리
        """
        return {
            "graph_type": "SimpleReactGraph",
            "pattern": "React (Reason + Act)",
            "workflow": "AI 에이전트가 스스로 도구 사용 판단",
            "model": self.model_name,
            "temperature": self.temperature,
        }


def create_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1, 
                search_settings: Optional[Dict[str, Any]] = None) -> SupervisedAgent:
    """
    Supervised Agent 인스턴스 생성 팩토리 함수
    
    Args:
        model_name: 사용할 OpenAI 모델명
        temperature: 모델의 창의성 수준
        search_settings: Tavily 검색 설정 (옵션)
    """
    return SupervisedAgent(model_name=model_name, temperature=temperature, search_settings=search_settings)


# 메인 실행 함수
def main():
    """
    대화형 에이전트 실행
    """
    print("=== PAI Web Agent 시작 ===")
    print("종료하려면 'quit', 'exit', 또는 'q'를 입력하세요.\n")
    
    try:
        # 에이전트 초기화
        agent = create_agent()
        thread_id = "main_conversation"
        
        while True:
            # 사용자 입력 받기
            user_input = input("질문: ").strip()
            
            # 종료 명령 확인
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("에이전트를 종료합니다.")
                break
            
            if not user_input:
                print("질문을 입력해주세요.")
                continue
            
            print("\n처리 중...")
            
            # 쿼리 처리
            result = agent.process_query(user_input, thread_id)
            
            if result["success"]:
                print(f"\n답변: {result['response']}\n")
            else:
                print(f"\n오류 발생: {result['error']}\n")
    
    except KeyboardInterrupt:
        print("\n\n에이전트가 중단되었습니다.")
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")


if __name__ == "__main__":
    main()
