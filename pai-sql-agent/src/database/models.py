"""
데이터베이스 모델 정의
데이터와 로직의 일체화 원칙에 따라 데이터 구조와 관련 로직을 함께 정의
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, BigInteger, 
    Boolean, JSON, ForeignKey, Index
)
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
    
    # 연령대별 인구 (추가 컬럼들)
    age_0_14 = Column(BigInteger, nullable=True, comment="0-14세 인구")
    age_15_64 = Column(BigInteger, nullable=True, comment="15-64세 인구")
    age_65_over = Column(BigInteger, nullable=True, comment="65세 이상 인구")
    
    __table_args__ = (
        Index("idx_population_year_adm", "year", "adm_cd"),
        Index("idx_population_adm_nm", "adm_nm"),
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
    avg_household_size = Column(Float, nullable=True, comment="평균 가구원수")
    
    # 가구 유형별
    one_person_household = Column(BigInteger, nullable=True, comment="1인 가구수")
    elderly_household = Column(BigInteger, nullable=True, comment="고령자 가구수")
    
    __table_args__ = (
        Index("idx_household_year_adm", "year", "adm_cd"),
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
    
    # 주택 유형별
    apartment_cnt = Column(BigInteger, nullable=True, comment="아파트수")
    detached_house_cnt = Column(BigInteger, nullable=True, comment="단독주택수")
    row_house_cnt = Column(BigInteger, nullable=True, comment="연립주택수")
    
    __table_args__ = (
        Index("idx_house_year_adm", "year", "adm_cd"),
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
    population = Column(BigInteger, nullable=True, comment="농가인구수(명)")
    avg_population = Column(Float, nullable=True, comment="농가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_farm_year_adm", "year", "adm_cd"),
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
    population = Column(BigInteger, nullable=True, comment="임가인구수(명)")
    avg_population = Column(Float, nullable=True, comment="임가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_forestry_year_adm", "year", "adm_cd"),
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
    population = Column(BigInteger, nullable=True, comment="어가인구수(명)")
    avg_population = Column(Float, nullable=True, comment="어가 평균 인구수(명)")
    
    __table_args__ = (
        Index("idx_fishery_year_adm_div", "year", "adm_cd", "oga_div"),
    )


class HouseholdMemberStats(Base, TimestampMixin):
    """가구원 통계 데이터"""
    __tablename__ = "household_member_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="기준연도")
    adm_cd = Column(String(20), nullable=False, comment="행정구역코드")
    adm_nm = Column(String(255), nullable=True, comment="행정구역명")
    data_type = Column(Integer, nullable=False, comment="가구타입(1:농가, 2:임가, 3:해수면어가, 4:내수면어가)")
    gender = Column(Integer, nullable=True, comment="성별(0:총합, 1:남자, 2:여자)")
    age_from = Column(Integer, nullable=True, comment="나이(from)")
    age_to = Column(Integer, nullable=True, comment="나이(to)")
    
    # 가구원 관련 지표
    population = Column(BigInteger, nullable=True, comment="가구원수(명)")
    
    __table_args__ = (
        Index("idx_member_year_adm_type", "year", "adm_cd", "data_type"),
    )


class CrawlLog(Base, TimestampMixin):
    """크롤링 로그"""
    __tablename__ = "crawl_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    api_endpoint = Column(String(255), nullable=False, comment="API 엔드포인트")
    year = Column(Integer, nullable=True, comment="요청 연도")
    adm_cd = Column(String(20), nullable=True, comment="행정구역코드")
    status = Column(String(50), nullable=False, comment="크롤링 상태")
    error_message = Column(Text, nullable=True, comment="에러 메시지")
    response_count = Column(Integer, nullable=True, comment="응답 데이터 개수")
    
    __table_args__ = (
        Index("idx_crawl_endpoint_status", "api_endpoint", "status"),
        Index("idx_crawl_created_at", "created_at"),
    )