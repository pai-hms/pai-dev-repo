"""
SQL Agent 헬퍼 유틸리티
공통 기능들을 모아놓은 유틸리티 모듈
"""
import re
from typing import Dict, List, Optional


class SchemaHelper:
    """스키마 정보 도우미"""
    
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
    
    # 포항시 상세
    POHANG_CODES = {
        "포항시": "47110",
        "포항시 남구": "47111",
        "포항시 북구": "47113"
    }
    
    @classmethod
    def get_region_code(cls, region_name: str) -> Optional[str]:
        """지역명으로 행정구역코드 조회"""
        # 직접 매치
        if region_name in cls.REGION_CODES:
            return cls.REGION_CODES[region_name]
        
        # 포항시 확인
        if "포항" in region_name:
            if "남구" in region_name:
                return cls.POHANG_CODES["포항시 남구"]
            elif "북구" in region_name:
                return cls.POHANG_CODES["포항시 북구"]
            else:
                return cls.POHANG_CODES["포항시"]
        
        # 부분 매치
        for name, code in cls.REGION_CODES.items():
            if region_name in name or name in region_name:
                return code
        
        return None
    
    @classmethod
    def get_relevant_tables(cls, question: str) -> List[str]:
        """질문에서 관련 테이블 추출"""
        question_lower = question.lower()
        tables = []
        
        if any(keyword in question_lower for keyword in ["인구", "평균연령", "나이"]):
            tables.append("population_stats")
            
        if any(keyword in question_lower for keyword in ["가구", "1인가구", "가구원"]):
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
    """쿼리 생성 도우미"""
    
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
        
        # 테이블별 쿼리 생성
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
    """응답 처리 도우미"""
    
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
                        # 숫자가 포함된 부분 찾기
                        for part in parts[1:]:
                            part = part.strip()
                            if part.isdigit():
                                return cls.format_number(part)
            return None
        except:
            return None


class ValidationHelper:
    """검증 도우미"""
    
    @classmethod
    def is_safe_query(cls, query: str) -> bool:
        """안전한 쿼리인지 확인"""
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER']
        query_upper = query.upper()
        
        return not any(keyword in query_upper for keyword in dangerous_keywords)
    
    @classmethod
    def has_valid_table(cls, query: str) -> bool:
        """유효한 테이블 사용 확인"""
        allowed_tables = [
            'population_stats', 'household_stats', 'house_stats', 
            'company_stats', 'farm_household_stats'
        ]
        
        query_lower = query.lower()
        return any(table in query_lower for table in allowed_tables)
