# rag-server/src/agent/state.py
from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

# Annotated와 operator.add를 사용하면,
# state 딕셔너리의 'messages' 키에 새로운 메시지가 추가될 때 기존 리스트에 덮어쓰지 않고 이어붙입니다.
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
