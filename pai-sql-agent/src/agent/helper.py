"""
SQL Agent 헬퍼 유틸리티
각종 도우미 기능을 제공하는 유틸리티 모듈

설계 원칙:
- KISS 원칙: 간단한 구조화된 클래스로 기능 분리
- 단방향 참조 원칙: 다른 모듈에서 이 모듈을 참조하되 순환 참조 금지
- Open-Closed Principle: 확장에는 열려 있고 수정에는 닫혀 있도록 설계
"""
import re
from typing import Dict, List, Optional, Any
from langchain_core.runnables import RunnableConfig


class SchemaHelper:
    """스키마 관련 헬퍼"""
    
    # 지역 코드 매핑
    REGION_CODES = {
        "서울특별시": "11", "서울": "11",
        "부산광역시": "26", "부산": "26",
        "대구광역시": "27", "대구": "27", 
        "인천광역시": "28", "인천": "28",
        "광주광역시": "29", "광주": "29",
        "대전광역시": "30", "대전": "30",
        "울산광역시": "31", "울산": "31",
        "세종특별자치시": "36", "세종": "36",
        "경기도": "41", "경기": "41",
        "강원특별자치도": "42", "강원": "42",
        "충청북도": "43", "충북": "43",
        "충청남도": "44", "충남": "44",
        "전북특별자치도": "45", "전북": "45",
        "전라남도": "46", "전남": "46",
        "경상북도": "47", "경북": "47",
        "경상남도": "48", "경남": "48",
        "제주특별자치도": "50", "제주": "50"
    }
    
    # 포항시 세부 코드
    POHANG_CODES = {
        "포항시": "47110",
        "포항시 북구": "47111",
        "포항시 남구": "47113"
    }
    
    @classmethod
    def get_region_code(cls, region_name: str) -> Optional[str]:
        """지역명으로 행정구역코드 조회"""
        # 직접 매칭
        if region_name in cls.REGION_CODES:
            return cls.REGION_CODES[region_name]
        
        # 포항시 세부 처리
        if "포항" in region_name:
            if "북구" in region_name:
                return cls.POHANG_CODES["포항시 북구"]
            elif "남구" in region_name:
                return cls.POHANG_CODES["포항시 남구"]
            else:
                return cls.POHANG_CODES["포항시"]
        
        # 부분 매칭
        for name, code in cls.REGION_CODES.items():
            if region_name in name or name in region_name:
                return code
        
        return None
    
    @classmethod
    def get_relevant_tables(cls, question: str) -> List[str]:
        """질문에서 관련 테이블 추출"""
        question_lower = question.lower()
        tables = []
        
        if any(keyword in question_lower for keyword in ["인구", "인구수", "나이"]):
            tables.append("population_stats")
            
        if any(keyword in question_lower for keyword in ["가구", "1인가구", "가구수"]):
            tables.append("household_stats")
            
        if any(keyword in question_lower for keyword in ["주택", "아파트"]):
            tables.append("house_stats")
            
        if any(keyword in question_lower for keyword in ["사업체", "회사", "기업"]):
            tables.append("company_stats")
        
        # 기본값
        if not tables:
            tables = ["population_stats"]
            
        return tables


class QueryHelper:
    """쿼리 생성 헬퍼"""
    
    @classmethod
    def extract_year(cls, question: str) -> int:
        """질문에서 연도 추출"""
        year_match = re.search(r'20\d{2}', question)
        return int(year_match.group()) if year_match else 2023
    
    @classmethod
    def build_simple_query(cls, question: str) -> str:
        """간단한 쿼리 템플릿 생성"""
        question_lower = question.lower()
        year = cls.extract_year(question)
        
        # 지역 추출
        region_code = None
        for region_name in SchemaHelper.REGION_CODES.keys():
            if region_name in question or region_name.replace("특별시", "").replace("광역시", "") in question:
                region_code = SchemaHelper.get_region_code(region_name)
                break
        
        if not region_code:
            return ""
        
        # 키워드별 쿼리 생성
        if "인구" in question_lower:
            return f"""
SELECT adm_nm, tot_ppltn, avg_age
FROM population_stats 
WHERE year = {year} AND adm_cd = '{region_code}';
""".strip()
        
        elif "사업체" in question_lower:
            return f"""
SELECT adm_nm, company_cnt, employee_cnt
FROM company_stats 
WHERE year = {year} AND adm_cd = '{region_code}';
""".strip()
        
        elif "가구" in question_lower:
            return f"""
SELECT adm_nm, household_cnt, one_person_household
FROM household_stats 
WHERE year = {year} AND adm_cd = '{region_code}';
""".strip()
        
        return ""


class ResponseHelper:
    """응답 처리 헬퍼"""
    
    @classmethod
    def format_number(cls, number: any) -> str:
        """숫자 포맷팅 (천단위 콤마)"""
        try:
            if isinstance(number, (int, float)):
                return f"{number:,}"
            elif isinstance(number, str) and number.isdigit():
                return f"{int(number):,}"
            else:
                return str(number)
        except:
            return str(number)
    
    @classmethod
    def extract_main_value(cls, execution_result: str) -> Optional[str]:
        """실행 결과에서 주요 값 추출"""
        try:
            lines = execution_result.split('\n')
            for line in lines:
                if '|' in line and not line.startswith('-'):
                    parts = line.split('|')
                    if len(parts) >= 2:
                        # 숫자인 부분을 찾기
                        for part in parts[1:]:
                            part = part.strip()
                            if part.isdigit():
                                return cls.format_number(part)
            return None
        except:
            return None


class ValidationHelper:
    """검증 헬퍼"""
    
    @classmethod
    def is_safe_query(cls, query: str) -> bool:
        """안전한 쿼리인지 검증"""
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER']
        query_upper = query.upper()
        
        return not any(keyword in query_upper for keyword in dangerous_keywords)
    
    @classmethod
    def has_valid_table(cls, query: str) -> bool:
        """허용된 테이블 사용 여부"""
        allowed_tables = [
            'population_stats', 'household_stats', 'house_stats', 
            'company_stats', 'farm_household_stats'
        ]
        
        query_lower = query.lower()
        return any(table in query_lower for table in allowed_tables)


class AgentHelper:
    """
    LangGraph에서 사용되는 service를 대체하되 최소한의 의존성 유지
    
    설계 원칙:
    - Container에 대한 의존성 최소화: 필요한 서비스만 DI로 주입받기
    - 단방향 참조 원칙: RunnableConfig 생성과 관련 기능만 담당
    """

    def __init__(
        self,
        chat_service=None,
        chatbot_service=None, 
        tool_service=None,
        guard_ruleset_service=None,
    ):
        """
        의존성 주입을 통한 초기화
        None 허용으로 선택적 서비스 의존성 주입 가능
        """
        self.chat_service = chat_service
        self.chatbot_service = chatbot_service
        self.tool_service = tool_service
        self.guard_ruleset_service = guard_ruleset_service

    async def validate_response(self, config: RunnableConfig, message: str) -> bool:
        """응답 검증 수행"""
        if not self.guard_ruleset_service:
            return True  # 서비스가 없으면 통과
            
        try:
            chatbot_id = config["configurable"]["chatbot"]["chatbot_id"]
            return await self.guard_ruleset_service.validate_response(chatbot_id, message)
        except Exception:
            return True  # 오류 시 통과로 처리
        
    async def get_runnable_config(
        self, session_id: str, user_payload: Any = None
    ) -> RunnableConfig:
        """
        RunnableConfig를 생성합니다.
        
        Args:
            session_id: 세션 ID
            user_payload: 사용자 정보 (선택적)
            
        Returns:
            RunnableConfig: LangGraph 실행용 설정 객체
        """
        try:
            # 기본 설정
            default_config = {
                "configurable": {
                    "thread_id": session_id,
                    "session_id": session_id,
                }
            }
            
            # 채팅 서비스가 있는 경우 세션 정보 추가
            if self.chat_service:
                try:
                    session = await self.chat_service.get_chat_session(session_id)
                    default_config["configurable"]["chatbot_id"] = session.chatbot_id
                    
                    # 챗봇 서비스가 있는 경우 챗봇 정보 추가
                    if self.chatbot_service and user_payload:
                        chatbot = await self.chatbot_service.get_user_chatbot(
                            session.chatbot_id, user_payload
                        )
                        default_config["configurable"]["chatbot"] = chatbot.to_dict()
                        
                except Exception:
                    pass  # 서비스 호출 실패 시 기본 설정 유지
            
            # 도구 서비스가 있는 경우 도구 설정 추가
            if self.tool_service and "chatbot_id" in default_config["configurable"]:
                try:
                    chatbot_id = default_config["configurable"]["chatbot_id"]
                    tools = await self.tool_service.find_by_chatbot_id(chatbot_id)
                    for tool in tools:
                        default_config['configurable'][tool.tool_agent_name] = tool.tool_config
                except Exception:
                    pass  # 도구 로딩 실패 시 무시
                    
            return default_config
            
        except Exception:
            # 모든 실패 시 최소한의 기본 설정 반환
            return {
                "configurable": {
                    "thread_id": session_id,
                    "session_id": session_id,
                }
            }

    def create_simple_config(self, thread_id: str, **kwargs) -> RunnableConfig:
        """
        간단한 RunnableConfig 생성 (빠른 생성)
        
        Args:
            thread_id: 스레드 ID
            **kwargs: 추가 설정
            
        Returns:
            RunnableConfig: 설정 객체
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
                "session_id": thread_id,
            }
        }
        
        # 추가 설정 병합
        if kwargs:
            config["configurable"].update(kwargs)
            
        return config
