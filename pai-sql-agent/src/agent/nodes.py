"""
SQL Agent 노드들
SLAP 원칙에 따라 동일한 추상화 수준으로 구성
"""
import logging
from typing import Dict, Any, TypedDict, List
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


# ===== 상태 정의 =====

class AgentState(TypedDict):
    """SQL Agent 상태 - 간소화"""
    messages: List[BaseMessage]
    current_query: str
    session_id: str
    
    # 분석 결과
    question_type: str      # SIMPLE, COMPLEX
    strategy: str           # DIRECT_SQL, REFUSE
    
    # SQL 관련
    generated_sql: str
    execution_result: str
    
    # 제어
    current_step: str
    is_complete: bool
    error_message: str
    used_tools: List[Dict[str, Any]]
    final_response: str


def create_initial_state(question: str, session_id: str = "default") -> AgentState:
    """초기 상태 생성"""
    return {
        "messages": [],
        "current_query": question,
        "session_id": session_id,
        
        "question_type": "",
        "strategy": "",
        
        "generated_sql": "",
        "execution_result": "",
        
        "current_step": "analyze",
        "is_complete": False,
        "error_message": "",
        "used_tools": [],
        "final_response": ""
    }


# ===== 노드 클래스들 =====

class QuestionAnalyzer:
    """질문 분석기"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def analyze(self, question: str) -> Dict[str, str]:
        """질문 분석"""
        try:
            prompt_template = """
질문을 분석하여 유형과 전략을 결정하세요.

질문: {question}

## 분석 기준
1. 질문 유형:
   - SIMPLE: 단일 지역, 단일 지표 ("서울 인구")
   - COMPLEX: 다중 지역 또는 복잡한 분석 ("서울과 부산 비교")

2. 전략:
   - DIRECT_SQL: 명확한 데이터 요청
   - REFUSE: 데이터 범위 외 또는 불가능한 요청

## 출력 형식
question_type: SIMPLE 또는 COMPLEX
strategy: DIRECT_SQL 또는 REFUSE
"""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm
            
            result = await chain.ainvoke({"question": question})
            content = result.content
            
            # 결과 파싱
            question_type = "SIMPLE"
            strategy = "DIRECT_SQL"
            
            if "COMPLEX" in content:
                question_type = "COMPLEX"
            if "REFUSE" in content:
                strategy = "REFUSE"
            
            return {
                "question_type": question_type,
                "strategy": strategy
            }
            
        except Exception as e:
            logger.error(f"질문 분석 오류: {e}")
            return {
                "question_type": "SIMPLE",
                "strategy": "REFUSE"
            }


class ResponseGenerator:
    """응답 생성기"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def generate(self, question: str, execution_result: str = "", error_message: str = "") -> str:
        """응답 생성"""
        try:
            if error_message:
                return f"죄송합니다. 질문 처리 중 오류가 발생했습니다: {error_message}"
            
            if not execution_result or "오류" in execution_result:
                return f"죄송합니다. '{question}'에 대한 데이터를 찾을 수 없습니다."
            
            # 성공 응답 생성
            prompt_template = """
질문에 대해 간결하고 명확하게 답변하세요.

질문: {question}
데이터: {execution_result}

답변 원칙:
1. 질문에 직접 답변
2. 간결하고 명확하게  
3. 핵심 정보만 포함

답변:
"""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm
            
            result = await chain.ainvoke({
                "question": question,
                "execution_result": execution_result
            })
            
            return result.content.strip()
            
        except Exception as e:
            logger.error(f"응답 생성 오류: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"


# ===== 노드 함수들 (LangGraph용) =====

async def analyze_question_node(state: AgentState) -> AgentState:
    """질문 분석 노드"""
    try:
        from .container import get_service
        
        analyzer = await get_service("question_analyzer")
        analysis = await analyzer.analyze(state["current_query"])
        
        return {
            **state,
            "question_type": analysis["question_type"],
            "strategy": analysis["strategy"],
            "current_step": "generate_sql",
            "messages": state["messages"] + [
                HumanMessage(content=state["current_query"])
            ]
        }
        
    except Exception as e:
        logger.error(f"질문 분석 노드 오류: {e}")
        return {
            **state,
            "error_message": f"질문 분석 실패: {str(e)}",
            "current_step": "error"
        }


async def generate_sql_node(state: AgentState) -> AgentState:
    """SQL 생성 노드"""
    try:
        # REFUSE 전략이면 SQL 생성 스킵
        if state["strategy"] == "REFUSE":
            return {
                **state,
                "current_step": "generate_response"
            }
        
        from .container import get_service
        
        generator = await get_service("sql_generator")
        sql_query = await generator.generate(state["current_query"])
        
        return {
            **state,
            "generated_sql": sql_query,
            "current_step": "execute_sql"
        }
        
    except Exception as e:
        logger.error(f"SQL 생성 노드 오류: {e}")
        return {
            **state,
            "error_message": f"SQL 생성 실패: {str(e)}",
            "current_step": "error"
        }


async def execute_sql_node(state: AgentState) -> AgentState:
    """SQL 실행 노드"""
    try:
        if not state["generated_sql"]:
            return {
                **state,
                "execution_result": "생성된 SQL이 없습니다.",
                "current_step": "generate_response"
            }
        
        from .container import get_service
        
        executor = await get_service("sql_executor")
        result = await executor.execute(state["generated_sql"])
        
        # 도구 사용 기록
        tool_record = {
            "tool_name": "execute_sql_query",
            "success": result["success"],
            "result_preview": result["result"][:200] if result["result"] else "",
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            **state,
            "execution_result": result["result"],
            "used_tools": state["used_tools"] + [tool_record],
            "current_step": "generate_response"
        }
        
    except Exception as e:
        logger.error(f"SQL 실행 노드 오류: {e}")
        return {
            **state,
            "error_message": f"SQL 실행 실패: {str(e)}",
            "current_step": "error"
        }


async def generate_response_node(state: AgentState) -> AgentState:
    """응답 생성 노드"""
    try:
        from .container import get_service
        
        generator = await get_service("response_generator")
        response = await generator.generate(
            question=state["current_query"],
            execution_result=state["execution_result"],
            error_message=state["error_message"]
        )
        
        return {
            **state,
            "final_response": response,
            "is_complete": True,
            "current_step": "completed",
            "messages": state["messages"] + [
                AIMessage(content=response)
            ]
        }
        
    except Exception as e:
        logger.error(f"응답 생성 노드 오류: {e}")
        return {
            **state,
            "final_response": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
            "is_complete": True,
            "current_step": "error"
        }


# ===== 라우팅 함수 =====

def should_continue(state: AgentState) -> str:
    """다음 단계 결정 - 선형 원리 적용"""
    current_step = state.get("current_step", "analyze")
    
    logger.info(f"🔄 라우팅 결정: current_step={current_step}, strategy={state.get('strategy', 'N/A')}")
    
    if current_step == "analyze":
        return "generate_sql"
    elif current_step == "generate_sql":
        if state.get("strategy") == "REFUSE":
            return "generate_response"
        return "execute_sql"
    elif current_step == "execute_sql":
        return "generate_response"
    elif current_step == "generate_response":
        return "end"
    elif current_step == "error":
        return "generate_response"
    else:
        logger.warning(f"⚠️ 예상치 못한 단계: {current_step}")
        return "end"