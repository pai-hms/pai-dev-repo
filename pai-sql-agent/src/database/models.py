"""
데이터베이스 모델 정의
통계청 및 SGIS API 데이터를 저장하기 위한 SQLAlchemy 모델들
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, BigInteger, 
    Boolean, JSON, ForeignKey, Index, UniqueConstraint, TIMESTAMP
)
# pgvector는 SQL에서만 사용, Python에서는 TEXT로 처리
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """타임스탬프 믹스인 (생성/수정 시간 자동 관리)"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class PopulationStats(Base, TimestampMixin):
    """인구 통계 데이터"""
    __tablename__ = "population_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 인구 관련 지표
    tot_ppltn = Column(BigInteger, nullable=True, comment="총인구")
    avg_age = Column(Float, nullable=True, comment="평균나이(세)")
    ppltn_dnsty = Column(Float, nullable=True, comment="인구밀도(명/㎢)")
    aged_child_idx = Column(Float, nullable=True, comment="노령화지수(일백명당 명)")
    oldage_suprt_per = Column(Float, nullable=True, comment="노년부양비(일백명당 명)")
    juv_suprt_per = Column(Float, nullable=True, comment="유년부양비(일백명당 명)")
    
    # 성별 인구
    male_ppltn = Column(BigInteger, nullable=True, comment="남자인구")
    female_ppltn = Column(BigInteger, nullable=True, comment="여자인구")
    
    # 연령별 인구 (주요 구간)
    age_0_14 = Column(BigInteger, nullable=True, comment="0-14세 인구")
    age_15_64 = Column(BigInteger, nullable=True, comment="15-64세 인구")
    age_65_over = Column(BigInteger, nullable=True, comment="65세 이상 인구")
    
    # 가구 및 주택 관련 (총조사에서 함께 제공)
    tot_family = Column(BigInteger, nullable=True, comment="총가구")
    avg_fmember_cnt = Column(Float, nullable=True, comment="평균가구원수")
    tot_house = Column(BigInteger, nullable=True, comment="총주택")
    nongga_cnt = Column(BigInteger, nullable=True, comment="농가(가구)")
    nongga_ppltn = Column(BigInteger, nullable=True, comment="농가 인구")
    imga_cnt = Column(BigInteger, nullable=True, comment="임가(가구)")
    imga_ppltn = Column(BigInteger, nullable=True, comment="임가 인구")
    naesuoga_cnt = Column(BigInteger, nullable=True, comment="내수면 어가(가구)")
    naesuoga_ppltn = Column(BigInteger, nullable=True, comment="내수면 어가 인구")
    haesuoga_cnt = Column(BigInteger, nullable=True, comment="해수면 어가(가구)")
    haesuoga_ppltn = Column(BigInteger, nullable=True, comment="해수면 어가인구")
    employee_cnt = Column(BigInteger, nullable=True, comment="종업원수(전체 사업체)")
    corp_cnt = Column(BigInteger, nullable=True, comment="사업체수(전체 사업체)")
    
    __table_args__ = (
        Index("idx_population_year_adm", "year", "adm_cd"),
        Index("idx_population_adm_nm", "adm_nm"),
        UniqueConstraint("year", "adm_cd", name="uq_population_year_adm"),
    )


class PopulationSearchStats(Base, TimestampMixin):
    """인구검색 세부 통계 (searchpopulation.json)"""
    __tablename__ = "population_search_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 검색 조건
    gender = Column(Integer, nullable=True, comment="성별(0:전체, 1:남자, 2:여자)")
    age_type = Column(String(10), nullable=True, comment="연령구분")
    edu_level = Column(String(10), nullable=True, comment="교육수준")
    mrg_state = Column(Integer, nullable=True, comment="혼인상태")
    
    # 결과값
    population = Column(BigInteger, nullable=True, comment="인구수")
    
    __table_args__ = (
        Index("idx_pop_search_year_adm", "year", "adm_cd"),
        Index("idx_pop_search_gender", "gender"),
        UniqueConstraint("year", "adm_cd", "gender", "age_type", "edu_level", "mrg_state", name="uq_pop_search_full"),
    )


class HouseholdStats(Base, TimestampMixin):
    """가구 통계 데이터"""
    __tablename__ = "household_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 가구 관련 지표
    household_cnt = Column(BigInteger, nullable=True, comment="가구수")
    family_member_cnt = Column(BigInteger, nullable=True, comment="가구원수")
    avg_household_size = Column(Float, nullable=True, comment="평균 가구원수")
    
    # 특수 가구
    one_person_household = Column(BigInteger, nullable=True, comment="1인 가구수")
    elderly_household = Column(BigInteger, nullable=True, comment="고령자 가구수")
    
    __table_args__ = (
        Index("idx_household_year_adm", "year", "adm_cd"),
        UniqueConstraint("year", "adm_cd", name="uq_household_year_adm"),
    )

class HouseStats(Base, TimestampMixin):
    """주택 통계 데이터"""
    __tablename__ = "house_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 주택 관련 지표
    house_cnt = Column(BigInteger, nullable=True, comment="주택수")
    apartment_cnt = Column(BigInteger, nullable=True, comment="아파트수")
    detached_house_cnt = Column(BigInteger, nullable=True, comment="단독주택수")
    row_house_cnt = Column(BigInteger, nullable=True, comment="연립주택수")
    
    __table_args__ = (
        Index("idx_house_year_adm", "year", "adm_cd"),
        UniqueConstraint("year", "adm_cd", name="uq_house_year_adm"),
    )

class CompanyStats(Base, TimestampMixin):
    """사업체 통계 데이터"""
    __tablename__ = "company_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 사업체 관련 지표
    company_cnt = Column(BigInteger, nullable=True, comment="사업체수")
    employee_cnt = Column(BigInteger, nullable=True, comment="종사자수")
    
    __table_args__ = (
        Index("idx_company_year_adm", "year", "adm_cd"),
        UniqueConstraint("year", "adm_cd", name="uq_company_year_adm"),
    )


class IndustryCodeStats(Base, TimestampMixin):
    """산업분류 코드 통계"""
    __tablename__ = "industry_code_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=True, comment="기준연도")
    adm_cd = Column(String(20), nullable=True, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    industry_cd = Column(String(10), nullable=True, comment="산업분류코드")
    industry_nm = Column(String(255), nullable=True, comment="산업분류명")
    
    # 산업별 통계
    company_cnt = Column(BigInteger, nullable=True, comment="사업체수")
    employee_cnt = Column(BigInteger, nullable=True, comment="종사자수")
    
    __table_args__ = (
        Index("idx_industry_code", "industry_cd"),
        UniqueConstraint("industry_cd", name="uq_industry_code"),
    )

class FarmHouseholdStats(Base, TimestampMixin):
    """농가 통계 데이터"""
    __tablename__ = "farm_household_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 농가 관련 지표
    farm_cnt = Column(BigInteger, nullable=True, comment="농가수(가구)")
    population = Column(BigInteger, nullable=True, comment="농가인구(명)")
    avg_population = Column(Float, nullable=True, comment="농가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_farm_year_adm", "year", "adm_cd"),
        UniqueConstraint("year", "adm_cd", name="uq_farm_year_adm"),
    )


class ForestryHouseholdStats(Base, TimestampMixin):
    """임가 통계 데이터"""
    __tablename__ = "forestry_household_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    
    # 임가 관련 지표
    forestry_cnt = Column(BigInteger, nullable=True, comment="임가수(가구)")
    population = Column(BigInteger, nullable=True, comment="임가인구(명)")
    avg_population = Column(Float, nullable=True, comment="임가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_forestry_year_adm", "year", "adm_cd"),
        UniqueConstraint("year", "adm_cd", name="uq_forestry_year_adm"),
    )


class FisheryHouseholdStats(Base, TimestampMixin):
    """어가 통계 데이터"""
    __tablename__ = "fishery_household_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    oga_div = Column(Integer, nullable=False, comment="어가구분(0:전체, 1:내수면, 2:해수면)")
    
    # 어가 관련 지표
    fishery_cnt = Column(BigInteger, nullable=True, comment="어가수(가구)")
    population = Column(BigInteger, nullable=True, comment="어가인구(명)")
    avg_population = Column(Float, nullable=True, comment="어가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_fishery_year_adm_div", "year", "adm_cd", "oga_div"),
        UniqueConstraint("year", "adm_cd", "oga_div", name="uq_fishery_year_adm_div"),
    )


class HouseholdMemberStats(Base, TimestampMixin):
    """가구원 통계 데이터"""
    __tablename__ = "household_member_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    data_type = Column(Integer, nullable=False, comment="가구타입(1:농가, 2:임가, 3:해수면어가, 4:내수면어가)")
    gender = Column(Integer, nullable=True, comment="성별(0:전체, 1:남자, 2:여자)")
    age_from = Column(Integer, nullable=True, comment="나이(from)")
    age_to = Column(Integer, nullable=True, comment="나이(to)")
    
    # 가구원 관련 지표
    population = Column(BigInteger, nullable=True, comment="가구원수(명)")
    
    __table_args__ = (
        Index("idx_member_year_adm_type", "year", "adm_cd", "data_type"),
        UniqueConstraint("year", "adm_cd", "data_type", "gender", "age_from", "age_to", name="uq_member_full"),
    )


# DocumentEmbedding 클래스는 SQL 벡터 독립적으로 처리
# SQLAlchemy 모델에서 pgvector 의존성 제거

class CrawlLog(Base, TimestampMixin):
    """크롤링 로그"""
    __tablename__ = "crawl_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    api_endpoint = Column(String(255), nullable=False, comment="API 엔드포인트")
    year = Column(Integer, nullable=True, comment="수집 연도")
    adm_cd = Column(String(20), nullable=True, comment="행정구역코드")
    status = Column(String(50), nullable=False, comment="처리 상태")
    error_message = Column(Text, nullable=True, comment="오류 메시지")
    response_count = Column(Integer, nullable=True, comment="응답 레코드 수")
    
    __table_args__ = (
        Index("idx_crawl_endpoint_status", "api_endpoint", "status"),
        Index("idx_crawl_created_at", "created_at"),
    )


class AgentSession(Base):
    """멀티턴 대화 세션 (SQL Agent 전용)"""
    __tablename__ = "agent_sessions"
    
    session_id = Column(String, primary_key=True)
    thread_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    user_id = Column(String, nullable=True)  # 향후 사용자 인증시 활용
    
    # 타임스탬프
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity = Column(TIMESTAMP, default=func.now(), nullable=False)
    
    # 세션 정보
    message_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 메타데이터 (JSON 형태로 저장)
    settings = Column(JSON, default={}, nullable=False)
    
    __table_args__ = (
        Index("idx_agent_sessions_thread_id", "thread_id"),
        Index("idx_agent_sessions_user_id", "user_id"),
        Index("idx_agent_sessions_activity", "last_activity"),
        Index("idx_agent_sessions_active", "is_active"),
    )