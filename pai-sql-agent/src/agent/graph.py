"""LangGraph 기반 SQL Agent 구현."""

from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.config import settings
from src.agent.nodes import LangAgentNode, LangGraphAgentState
from src.agent.prompt import PromptGenerator
from src.agent.tools import SQLQueryTool, SchemaInfoToolWrapper
from src.agent.checkpointer import PostgreSQLCheckpointSaver


class SQLAgent:
    """설계 원칙을 따르는 지방자치단체 예산 분석용 SQL 에이전트."""
    
    def __init__(self):
        """SQL 에이전트 초기화."""
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        
        # 도구 초기화
        self.sql_tool = SQLQueryTool()
        self.schema_tool = SchemaInfoToolWrapper()
        self.tools = {"sql_agent": self.sql_tool, "schema_info": self.schema_tool}
        
        # 프롬프트 생성기 초기화
        self.prompt_generator = PromptGenerator()
        
        # 체크포인터 초기화
        self.checkpointer = PostgreSQLCheckpointSaver()
        
        # 그래프 구축
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        """선형 원리를 따르는 에이전트 그래프 구축."""
        # 노드 선언
        tools = [self.sql_tool, self.schema_tool]
        
        agent_node = LangAgentNode(
            llm=self.llm,
            tools=self.tools,
            prompt_generator=self.prompt_generator,
        )
        tool_node = ToolNode(tools)

        # 그래프 생성
        graph = (
            StateGraph(LangGraphAgentState)
            .add_node("agent", agent_node)
            .add_node("tools", tool_node)
            .set_entry_point("agent")
            .add_conditional_edges("agent", tools_condition)
            .add_edge("tools", "agent")
        )

        # 체크포인터와 함께 컴파일
        return graph.compile(checkpointer=self.checkpointer)

    async def process_question(
        self, 
        question: str, 
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 질문을 처리하고 응답 반환."""
        from datetime import datetime
        from langchain_core.messages import HumanMessage
        
        # 초기 상태 생성
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "query": question,
            "sql_query": "",
            "data": {},
        }
        
        # 영속성을 위한 thread_id 설정
        config = {
            "configurable": {
                "thread_id": thread_id or f"thread_{datetime.now().isoformat()}",
                "sql_agent": True,
            }
        }
        
        # 그래프 실행
        final_state = await self.graph.ainvoke(initial_state, config)
        
        # 최종 응답 추출
        messages = final_state["messages"]
        final_message = messages[-1] if messages else None
        
        return {
            "response": final_message.content if final_message else "응답이 생성되지 않았습니다",
            "thread_id": config["configurable"]["thread_id"],
            "sql_query": final_state.get("sql_query"),
            "data": final_state.get("data"),
        }
    
    async def stream_response(
        self, 
        question: str, 
        thread_id: Optional[str] = None
    ):
        """실시간 업데이트를 위한 에이전트 응답 스트리밍."""
        from datetime import datetime
        from langchain_core.messages import HumanMessage
        
        # 초기 상태 생성
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "query": question,
            "sql_query": "",
            "data": {},
        }
        
        # 영속성을 위한 thread_id 설정
        config = {
            "configurable": {
                "thread_id": thread_id or f"thread_{datetime.now().isoformat()}",
                "sql_agent": True,
            }
        }
        
        # 그래프 실행 스트리밍
        async for chunk in self.graph.astream(initial_state, config):
            yield chunk


def create_sql_agent() -> CompiledStateGraph:
    """SQL 에이전트를 생성합니다."""
    agent = SQLAgent()
    return agent.graph


class AgentService:
    """데이터 주권 원칙을 따르는 SQL 에이전트 서비스 레이어."""
    
    def __init__(self):
        self.agent = SQLAgent()
    
    async def ask_question(
        self, 
        question: str, 
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """SQL 에이전트에게 질문하기."""
        try:
            result = await self.agent.process_question(question, thread_id)
            return {
                "success": True,
                "data": result,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
            }
    
    async def stream_question(
        self, 
        question: str, 
        thread_id: Optional[str] = None
    ):
        """실시간 업데이트를 위한 에이전트 응답 스트리밍."""
        try:
            async for chunk in self.agent.stream_response(question, thread_id):
                yield {
                    "success": True,
                    "data": chunk,
                    "error": None,
                }
        except Exception as e:
            yield {
                "success": False,
                "data": None,
                "error": str(e),
            }
