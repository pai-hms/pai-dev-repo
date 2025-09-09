"""
데이터베이스 초기 데이터 로딩
SGIS API에서 센서스 통계 데이터를 크롤링하여 데이터베이스에 저장
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.config.settings import get_settings
from src.database.connection import get_database_manager
from src.database.repository import DatabaseService
from src.crawler.sgis_client import SGISClient, SGISDataType


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataInitializer:
    """데이터 초기화 클래스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        self.sgis_client = SGISClient()
        
        # 크롤링할 연도 범위
        self.population_years = list(range(2015, 2024))  # 2015-2023
        self.company_years = list(range(2000, 2024))     # 2000-2023
        self.farm_years = [2000, 2005, 2010, 2015, 2020]  # 농림어업총조사 연도
        self.industry_years = [2021, 2022, 2023]  # 산업분류 연도

    async def initialize_all_data(self) -> None:
        """
        모든 SGIS API 데이터 초기화 (총 10개 API)
        
        API 구성:
        1. 총조사 주요지표 (population.json) - 종합 통계
        2. 인구통계 (searchpopulation.json) - 세부 인구 검색
        3. 가구통계 (household.json)
        4. 주택통계 (house.json)
        5. 사업체통계 (company.json)
        6. 산업분류 (industrycode.json)
        7. 농가통계 (farmhousehold.json)
        8. 임가통계 (forestryhousehold.json)
        9. 어가통계 (fisheryhousehold.json)
        10. 가구원통계 (householdmember.json)
        """
        logger.info("SGIS 데이터 초기화 시작 (10개 API 독립 구현)")
        
        try:
            # API 키 확인
            if not self.settings.sgis_service_id or not self.settings.sgis_security_key:
                logger.error("SGIS API 키가 설정되지 않았습니다.")
                logger.error(f"SGIS_SERVICE_ID: {self.settings.sgis_service_id}")
                logger.error(f"SGIS_SECURITY_KEY: {'*' * len(self.settings.sgis_security_key) if self.settings.sgis_security_key else 'None'}")
                raise ValueError("SGIS API 키를 설정해주세요")
            
            # 행정구역 정보 조회
            divisions = await self.sgis_client.get_all_administrative_divisions()
            logger.info(f"행정구역 {len(divisions)}개 조회 완료")
            
            # 1. 총조사 주요지표 (종합 통계)
            await self._init_census_main_indicators()
            
            # 2. 인구통계 (세부 검색)
            await self._init_population_search_data()
            
            # 3. 가구통계
            await self._init_household_data()
            
            # 4. 주택통계
            await self._init_house_data()
            
            # 5. 사업체통계
            await self._init_company_data()
            
            # 6. 산업분류
            await self._init_industry_code_data()
            
            # 7. 농가통계 (독립 구현)
            await self._init_farm_household_data()
            
            # 8. 임가통계 (독립 구현)
            await self._init_forestry_household_data()
            
            # 9. 어가통계 (독립 구현)
            await self._init_fishery_household_data()
            
            # 10. 가구원통계
            await self._init_household_member_data()
            
            logger.info("SGIS 데이터 초기화 완료 (10개 API 모두 독립 처리)")
            
        except Exception as e:
            logger.error(f"데이터 초기화 실패: {str(e)}")
            raise

    # ==========================================
    # 1. 총조사 주요지표 (population.json)
    # ==========================================
    async def _init_census_main_indicators(self) -> None:
        """
        1. 총조사 주요지표 데이터 초기화
        API: /stats/population.json
        설명: 인구, 가구, 주택, 사업체 등 종합 통계 지표
        """
        logger.info("1. 총조사 주요지표 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"총조사 주요지표 {year}년 데이터 처리 중...")
                
                try:
                    # 전국 시도 데이터 수집
                    response = await self.sgis_client.get_population_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_census_main_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.population.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/population.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"총조사 주요지표 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/population.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"총조사 주요지표 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 2. 인구통계 (searchpopulation.json)
    # ==========================================
    async def _init_population_search_data(self) -> None:
        """
        2. 인구통계 검색 데이터 수집
        API: /stats/searchpopulation.json
        설명: 성별, 연령대별 세부 인구 통계
        """
        logger.info("2. 인구통계 검색 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 전국 시도별 데이터 수집
            for year in self.population_years:
                logger.info(f"인구통계 검색 {year}년 데이터 처리 중...")
                
                try:
                    # 전국 시도 데이터 검색 (adm_cd 없이 호출하면 전국 시도 목록)
                    response = await self.sgis_client.search_population_stats(
                        year=year,
                        gender=0,  # 전체
                        low_search=1
                    )
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_population_search_data(item, year, gender=0)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.population_search.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/searchpopulation.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"인구통계 검색 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/searchpopulation.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"인구통계 검색 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 3. 가구통계 (household.json)
    # ==========================================
    async def _init_household_data(self) -> None:
        """
        3. 가구통계 데이터 초기화
        API: /stats/household.json
        응답: household_cnt, family_member_cnt, avg_family_member_cnt
        """
        logger.info("3. 가구통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"가구통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_household_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_household_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.household.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/household.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"가구통계 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/household.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"가구통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 4. 주택통계 (house.json)
    # ==========================================
    async def _init_house_data(self) -> None:
        """
        4. 주택통계 데이터 초기화
        API: /stats/house.json
        응답: house_cnt
        """
        logger.info("4. 주택통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"주택통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_house_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_house_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.house.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/house.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"주택통계 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)

                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/house.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"주택통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 5. 사업체통계 (company.json)
    # ==========================================
    async def _init_company_data(self) -> None:
        """
        5. 사업체통계 데이터 초기화
        API: /stats/company.json
        응답: corp_cnt, tot_worker
        """
        logger.info("5. 사업체통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.company_years:
                logger.info(f"사업체통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_company_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_company_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.company.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/company.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"사업체통계 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/company.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"사업체통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 6. 산업분류 (industrycode.json)
    # ==========================================
    async def _init_industry_code_data(self) -> None:
        """
        6. 산업분류 코드 데이터 초기화
        API: /stats/industrycode.json
        응답: class_code, class_nm
        """
        logger.info("6. 산업분류 코드 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 10차 산업분류 (2017년~)
            try:
                response = await self.sgis_client.get_industry_code(class_deg="10")
                
                if response.is_success:
                    data_list = []
                    
                    for item in response.result:
                        data = self._convert_industry_code_data(item)
                        if data:
                            data_list.append(data)
                    
                    if data_list:
                        await db_service.industry.upsert_batch(data_list)
                        await db_service.crawl_log.log_success(
                            api_endpoint="/stats/industrycode.json",
                            year=None,
                            response_count=len(data_list)
                        )
                        logger.info(f"산업분류 코드: {len(data_list)}개 레코드 처리")
                
            except Exception as e:
                await db_service.crawl_log.log_error(
                    api_endpoint="/stats/industrycode.json",
                    year=None,
                    error_message=str(e)
                )
                logger.error(f"산업분류 코드 처리 실패: {str(e)}")

    # ==========================================
    # 7. 농가통계 (farmhousehold.json)
    # ==========================================
    async def _init_farm_household_data(self) -> None:
        """
        7. 농가통계 데이터 초기화
        API: /stats/farmhousehold.json
        응답: farm_cnt, population, avg_population
        """
        logger.info("7. 농가통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.farm_years:
                logger.info(f"농가통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_farm_household_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_farm_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.farm_household.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/farmhousehold.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"농가통계 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/farmhousehold.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"농가통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 8. 임가통계 (forestryhousehold.json)
    # ==========================================
    async def _init_forestry_household_data(self) -> None:
        """
        8. 임가통계 데이터 초기화
        API: /stats/forestryhousehold.json
        응답: forestry_cnt, population, avg_population
        """
        logger.info("8. 임가통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            
            # 임가통계는 2005년부터 제공
            forestry_years = [year for year in self.farm_years if year >= 2005]
            
            for year in forestry_years:
                logger.info(f"임가통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_forestry_household_stats(year=year, low_search=1)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_forestry_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.forestry_household.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/forestryhousehold.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"임가통계 {year}년: {len(data_list)}개 레코드 처리")
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/forestryhousehold.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"임가통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 9. 어가통계 (fisheryhousehold.json)
    # ==========================================
    async def _init_fishery_household_data(self) -> None:
        """
        9. 어가통계 데이터 초기화
        API: /stats/fisheryhousehold.json
        응답: fishery_cnt, population, avg_population
        """
        logger.info("9. 어가통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 어가통계는 2005년부터 제공
            fishery_years = [year for year in self.farm_years if year >= 2005]
            
            for year in fishery_years:
                logger.info(f"어가통계 {year}년 데이터 처리 중...")
                
                try:
                    # 전체, 내수면, 해수면 어가 각각 처리
                    for oga_div in [0, 1, 2]:
                        logger.info(f"어가통계 {year}년 구분{oga_div} 처리 중...")
                        
                        response = await self.sgis_client.get_fishery_household_stats(
                            year=year, 
                            oga_div=oga_div,
                            low_search=1
                        )
                        
                        if response.is_success:
                            data_list = []
                            
                            for item in response.result:
                                data = self._convert_fishery_data(item, year, oga_div)
                                if data:
                                    data_list.append(data)
                            
                            if data_list:
                                await db_service.fishery_household.upsert_batch(data_list)
                                await db_service.crawl_log.log_success(
                                    api_endpoint=f"/stats/fisheryhousehold.json (div={oga_div})",
                                    year=year,
                                    response_count=len(data_list)
                                )
                                logger.info(f"어가통계 {year}년 구분{oga_div}: {len(data_list)}개 레코드 처리")
                        
                        await asyncio.sleep(0.3)
                    
                except Exception as e:
                    await db_service.crawl_log.log_error(
                        api_endpoint="/stats/fisheryhousehold.json",
                        year=year,
                        error_message=str(e)
                    )
                    logger.error(f"어가통계 {year}년 처리 실패: {str(e)}")

    # ==========================================
    # 10. 가구원통계 (householdmember.json)
    # ==========================================
    async def _init_household_member_data(self) -> None:
        """
        10. 가구원통계 데이터 초기화
        API: /stats/householdmember.json
        응답: population (가구원수)
        """
        logger.info("10. 가구원통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 가구 타입별 데이터 수집
            data_types = [1, 2, 3, 4]  # 1:농가, 2:임가, 3:해수면어가, 4:내수면어가
            
            for year in self.farm_years:
                for data_type in data_types:
                    logger.info(f"가구원통계 {year}년 타입{data_type} 데이터 처리 중...")
                    
                    try:
                        response = await self.sgis_client.get_household_member_stats(
                            year=year,
                            data_type=data_type,
                            low_search=1
                        )
                        
                        if response.is_success:
                            data_list = []
                            
                            for item in response.result:
                                data = self._convert_household_member_data(item, year, data_type)
                                if data:
                                    data_list.append(data)
                            
                            if data_list:
                                await db_service.household_member.upsert_batch(data_list)
                                await db_service.crawl_log.log_success(
                                    api_endpoint=f"/stats/householdmember.json (type={data_type})",
                                    year=year,
                                    response_count=len(data_list)
                                )
                                logger.info(f"가구원통계 {year}년 타입{data_type}: {len(data_list)}개 레코드 처리")
                            else:
                                logger.warning(f"가구원통계 {year}년 타입{data_type}: 변환 가능한 데이터 없음")
                    
                        await asyncio.sleep(0.3)
                    
                    except Exception as e:
                        await db_service.crawl_log.log_error(
                            api_endpoint=f"/stats/householdmember.json (type={data_type})",
                            year=year,
                            error_message=str(e)
                        )
                        logger.error(f"가구원통계 {year}년 타입{data_type} 처리 실패: {str(e)}")


    # ==========================================
    # 데이터 변환 함수들 (API 응답 완전 반영)
    # ==========================================
    def _convert_census_main_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        총조사 주요지표 데이터 변환 (population.json)
        
        API 응답 필드 (모든 필드 활용):
        - tot_ppltn: 총인구
        - avg_age: 평균나이(세)
        - ppltn_dnsty: 인구밀도(명/㎢)
        - aged_child_idx: 노령화지수(일백명당 명)
        - oldage_suprt_per: 노년부양비(일백명당 명)
        - juv_suprt_per: 유년부양비(일백명당 명)
        - tot_family: 총가구
        - avg_fmember_cnt: 평균가구원수
        - tot_house: 총주택
        - nongga_cnt: 농가(가구)
        - nongga_ppltn: 농가 인구
        - imga_cnt: 임가(가구)
        - imga_ppltn: 임가 인구
        - naesuoga_cnt: 내수면 어가(가구)
        - naesuoga_ppltn: 내수면 어가 인구
        - haesuoga_cnt: 해수면 어가(가구)
        - haesuoga_ppltn: 해수면 어가인구
        - employee_cnt: 종업원수(전체 사업체)
        - corp_cnt: 사업체수(전체 사업체)
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                # 인구 관련
                "tot_ppltn": self._safe_int(item.get("tot_ppltn")),
                "avg_age": self._safe_float(item.get("avg_age")),
                "ppltn_dnsty": self._safe_float(item.get("ppltn_dnsty")),
                "aged_child_idx": self._safe_float(item.get("aged_child_idx")),
                "oldage_suprt_per": self._safe_float(item.get("oldage_suprt_per")),
                "juv_suprt_per": self._safe_float(item.get("juv_suprt_per")),
                # 추가 종합 지표들 (별도 테이블에 저장 가능)
                "tot_family": self._safe_int(item.get("tot_family")),
                "avg_fmember_cnt": self._safe_float(item.get("avg_fmember_cnt")),
                "tot_house": self._safe_int(item.get("tot_house")),
                "nongga_cnt": self._safe_int(item.get("nongga_cnt")),
                "nongga_ppltn": self._safe_int(item.get("nongga_ppltn")),
                "imga_cnt": self._safe_int(item.get("imga_cnt")),
                "imga_ppltn": self._safe_int(item.get("imga_ppltn")),
                "naesuoga_cnt": self._safe_int(item.get("naesuoga_cnt")),
                "naesuoga_ppltn": self._safe_int(item.get("naesuoga_ppltn")),
                "haesuoga_cnt": self._safe_int(item.get("haesuoga_cnt")),
                "haesuoga_ppltn": self._safe_int(item.get("haesuoga_ppltn")),
                "employee_cnt": self._safe_int(item.get("employee_cnt")),
                "corp_cnt": self._safe_int(item.get("corp_cnt")),
            }
        except Exception as e:
            logger.error(f"총조사 주요지표 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_population_search_data(self, item: Dict[str, Any], year: int, gender: int = 0) -> Optional[Dict[str, Any]]:
        """
        인구통계 검색 데이터 변환 (searchpopulation.json)
        
        API 응답 필드:
        - adm_cd: 행정구역코드
        - adm_nm: 행정구역명
        - population: 인구수
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "gender": gender,
                "age_type": None,
                "edu_level": None,
                "mrg_state": None,
                "population": self._safe_int(item.get("population")),
            }
        except Exception as e:
            logger.error(f"인구통계 검색 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_household_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        가구통계 데이터 변환 (household.json)
        API 응답: household_cnt, family_member_cnt, avg_family_member_cnt
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "household_cnt": self._safe_int(item.get("household_cnt")),
                "family_member_cnt": self._safe_int(item.get("family_member_cnt")),
                "avg_household_size": self._safe_float(item.get("avg_family_member_cnt")),
            }
        except Exception as e:
            logger.error(f"가구 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_house_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        주택통계 데이터 변환 (house.json)
        API 응답: house_cnt
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "house_cnt": self._safe_int(item.get("house_cnt")),
                # API에서 제공하지 않는 세부 주택 유형은 NULL
                "apartment_cnt": None,
                "detached_house_cnt": None,
                "row_house_cnt": None,
            }
        except Exception as e:
            logger.error(f"주택 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_company_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        사업체통계 데이터 변환 (company.json)
        API 응답: corp_cnt, tot_worker
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "company_cnt": self._safe_int(item.get("corp_cnt")),
                "employee_cnt": self._safe_int(item.get("tot_worker")),
            }
        except Exception as e:
            logger.error(f"사업체 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_industry_code_data(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        산업분류 코드 데이터 변환 (industrycode.json)
        API 응답: class_code, class_nm
        """
        try:
            return {
                "year": None,  # 산업분류는 연도별이 아님
                "adm_cd": None,
                "adm_nm": None,
                "industry_cd": item.get("class_code"),
                "industry_nm": item.get("class_nm"),
                "company_cnt": None,
                "employee_cnt": None,
            }
        except Exception as e:
            logger.error(f"산업분류 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_farm_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        농가통계 데이터 변환 (farmhousehold.json)
        API 응답: farm_cnt, population, avg_population
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "farm_cnt": self._safe_int(item.get("farm_cnt")),
                "population": self._safe_int(item.get("population")),
                "avg_population": self._safe_float(item.get("avg_population")),
            }
        except Exception as e:
            logger.error(f"농가 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_forestry_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """
        임가통계 데이터 변환 (forestryhousehold.json)
        API 응답: forestry_cnt, population, avg_population
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "forestry_cnt": self._safe_int(item.get("forestry_cnt")),
                "population": self._safe_int(item.get("population")),
                "avg_population": self._safe_float(item.get("avg_population")),
            }
        except Exception as e:
            logger.error(f"임가 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_fishery_data(self, item: Dict[str, Any], year: int, oga_div: int) -> Optional[Dict[str, Any]]:
        """
        어가통계 데이터 변환 (fisheryhousehold.json)
        API 응답: fishery_cnt, population, avg_population
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "oga_div": oga_div,
                "fishery_cnt": self._safe_int(item.get("fishery_cnt")),
                "population": self._safe_int(item.get("population")),
                "avg_population": self._safe_float(item.get("avg_population")),
            }
        except Exception as e:
            logger.error(f"어가 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    def _convert_household_member_data(self, item: Dict[str, Any], year: int, data_type: int) -> Optional[Dict[str, Any]]:
        """
        가구원통계 데이터 변환 (householdmember.json)
        
        API 응답 필드:
        - adm_cd: 행정구역코드
        - adm_nm: 행정구역명
        - gender: 성별
        - age_from: 나이(from)
        - age_to: 나이(to)
        - population: 가구원수(명)
        """
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "data_type": data_type,
                "gender": self._safe_int(item.get("gender")),
                "age_from": self._safe_int(item.get("age_from")),
                "age_to": self._safe_int(item.get("age_to")),
                "population": self._safe_int(item.get("population")),
            }
        except Exception as e:
            logger.error(f"가구원 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None

    # ==========================================
    # 유틸리티 함수들
    # ==========================================
    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """안전한 정수 변환"""
        if value is None or value == "" or value == "N/A":
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """안전한 실수 변환"""
        if value is None or value == "" or value == "N/A":
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None


async def main():
    """메인 함수"""
    try:
        initializer = DataInitializer()
        await initializer.initialize_all_data()
        print("✓ SGIS 데이터 초기화가 완료되었습니다.")
    except Exception as e:
        print(f"X 데이터 초기화 실패: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())