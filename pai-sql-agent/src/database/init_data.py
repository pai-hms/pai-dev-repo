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
    
    async def initialize_all_data(self) -> None:
        """모든 데이터 초기화"""
        logger.info("데이터 초기화 시작")
        
        try:
            # 행정구역 목록 조회
            divisions = await self.sgis_client.get_all_administrative_divisions()
            logger.info(f"행정구역 {len(divisions)}개 조회 완료")
            
            # 각 통계 데이터 초기화
            await self._init_population_data(divisions)
            await self._init_household_data(divisions)
            await self._init_house_data(divisions)
            await self._init_company_data(divisions)
            await self._init_farm_data(divisions)
            
            logger.info("데이터 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터 초기화 실패: {str(e)}")
            raise
    
    async def _init_population_data(self, divisions: List[Dict[str, str]]) -> None:
        """인구 통계 데이터 초기화"""
        logger.info("인구 통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"인구 통계 {year}년 데이터 처리 중...")
                
                try:
                    # 전국 데이터 먼저 수집
                    response = await self.sgis_client.get_population_stats(year=year)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_population_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            await db_service.population.upsert_batch(data_list)
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/population.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"인구 통계 {year}년: {len(data_list)}개 레코드 처리")
                    else:
                        await db_service.crawl_log.log_error(
                            api_endpoint="/stats/population.json",
                            year=year,
                            error_message=response.error_message or "Unknown error"
                        )
                        logger.error(f"인구 통계 {year}년 API 호출 실패: {response.error_message}")
                
                except Exception as e:
                    async with self.db_manager.get_async_session() as log_session:
                        log_service = DatabaseService(log_session)
                        await log_service.crawl_log.log_error(
                            api_endpoint="/stats/population.json",
                            year=year,
                            error_message=str(e)
                        )
                    logger.error(f"인구 통계 {year}년 처리 실패: {str(e)}")
                
                # API 호출 간격 조정
                await asyncio.sleep(0.5)
    
    async def _init_household_data(self, divisions: List[Dict[str, str]]) -> None:
        """가구 통계 데이터 초기화"""
        logger.info("가구 통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"가구 통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_household_stats(year=year)
                    
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
                            logger.info(f"가구 통계 {year}년: {len(data_list)}개 레코드 처리")
                
                except Exception as e:
                    logger.error(f"가구 통계 {year}년 처리 실패: {str(e)}")
                
                await asyncio.sleep(0.5)
    
    async def _init_house_data(self, divisions: List[Dict[str, str]]) -> None:
        """주택 통계 데이터 초기화"""
        logger.info("주택 통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.population_years:
                logger.info(f"주택 통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_house_stats(year=year)
                    
                    if response.is_success:
                        data_list = []
                        
                        for item in response.result:
                            data = self._convert_house_data(item, year)
                            if data:
                                data_list.append(data)
                        
                        if data_list:
                            # HouseStats 모델이 없으므로 로그만 기록
                            await db_service.crawl_log.log_success(
                                api_endpoint="/stats/house.json",
                                year=year,
                                response_count=len(data_list)
                            )
                            logger.info(f"주택 통계 {year}년: {len(data_list)}개 레코드 처리")
                
                except Exception as e:
                    logger.error(f"주택 통계 {year}년 처리 실패: {str(e)}")
                
                await asyncio.sleep(0.5)
    
    async def _init_company_data(self, divisions: List[Dict[str, str]]) -> None:
        """사업체 통계 데이터 초기화"""
        logger.info("사업체 통계 데이터 초기화 시작")
        
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            for year in self.company_years:
                logger.info(f"사업체 통계 {year}년 데이터 처리 중...")
                
                try:
                    response = await self.sgis_client.get_company_stats(year=year)
                    
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
                            logger.info(f"사업체 통계 {year}년: {len(data_list)}개 레코드 처리")
                
                except Exception as e:
                    logger.error(f"사업체 통계 {year}년 처리 실패: {str(e)}")
                
                await asyncio.sleep(0.5)
    
    async def _init_farm_data(self, divisions: List[Dict[str, str]]) -> None:
        """농림어업 통계 데이터 초기화"""
        logger.info("농림어업 통계 데이터 초기화 시작")
        
        for year in self.farm_years:
            logger.info(f"농림어업 통계 {year}년 데이터 처리 중...")
            
            try:
                # 농가 통계
                await self._process_farm_household_data(year)
                await asyncio.sleep(0.3)
                
                # 임가 통계
                await self._process_forestry_household_data(year)
                await asyncio.sleep(0.3)
                
                # 어가 통계
                await self._process_fishery_household_data(year)
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"농림어업 통계 {year}년 처리 실패: {str(e)}")
    
    async def _process_farm_household_data(self, year: int) -> None:
        """농가 통계 데이터 처리"""
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            try:
                response = await self.sgis_client.get_farm_household_stats(year=year)
                
                if response.is_success and response.result:
                    await db_service.crawl_log.log_success(
                        api_endpoint="/stats/farmhousehold.json",
                        year=year,
                        response_count=len(response.result)
                    )
                    logger.info(f"농가 통계 {year}년: {len(response.result)}개 레코드")
                
            except Exception as e:
                await db_service.crawl_log.log_error(
                    api_endpoint="/stats/farmhousehold.json",
                    year=year,
                    error_message=str(e)
                )
    
    async def _process_forestry_household_data(self, year: int) -> None:
        """임가 통계 데이터 처리"""
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            try:
                response = await self.sgis_client.get_forestry_household_stats(year=year)
                
                if response.is_success and response.result:
                    await db_service.crawl_log.log_success(
                        api_endpoint="/stats/forestryhousehold.json",
                        year=year,
                        response_count=len(response.result)
                    )
                    logger.info(f"임가 통계 {year}년: {len(response.result)}개 레코드")
                
            except Exception as e:
                await db_service.crawl_log.log_error(
                    api_endpoint="/stats/forestryhousehold.json",
                    year=year,
                    error_message=str(e)
                )
    
    async def _process_fishery_household_data(self, year: int) -> None:
        """어가 통계 데이터 처리"""
        async with self.db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            try:
                # 전체, 내수면, 해수면 어가 각각 처리
                for oga_div in [0, 1, 2]:
                    response = await self.sgis_client.get_fishery_household_stats(
                        year=year, oga_div=oga_div
                    )
                    
                    if response.is_success and response.result:
                        await db_service.crawl_log.log_success(
                            api_endpoint=f"/stats/fisheryhousehold.json (div={oga_div})",
                            year=year,
                            response_count=len(response.result)
                        )
                        logger.info(f"어가 통계 {year}년 구분{oga_div}: {len(response.result)}개 레코드")
                    
                    await asyncio.sleep(0.2)
                
            except Exception as e:
                await db_service.crawl_log.log_error(
                    api_endpoint="/stats/fisheryhousehold.json",
                    year=year,
                    error_message=str(e)
                )
    
    def _convert_population_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """SGIS 인구 통계 데이터를 DB 모델 형태로 변환"""
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "tot_ppltn": self._safe_int(item.get("tot_ppltn")),
                "avg_age": self._safe_float(item.get("avg_age")),
                "ppltn_dnsty": self._safe_float(item.get("ppltn_dnsty")),
                "aged_child_idx": self._safe_float(item.get("aged_child_idx")),
                "oldage_suprt_per": self._safe_float(item.get("oldage_suprt_per")),
                "juv_suprt_per": self._safe_float(item.get("juv_suprt_per")),
                "male_ppltn": self._safe_int(item.get("male_ppltn")),
                "female_ppltn": self._safe_int(item.get("female_ppltn")),
            }
        except Exception as e:
            logger.error(f"인구 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None
    
    def _convert_household_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """SGIS 가구 통계 데이터를 DB 모델 형태로 변환"""
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "household_cnt": self._safe_int(item.get("household_cnt")),
                "avg_household_size": self._safe_float(item.get("avg_household_size")),
            }
        except Exception as e:
            logger.error(f"가구 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None
    
    def _convert_house_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """SGIS 주택 통계 데이터를 DB 모델 형태로 변환"""
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "house_cnt": self._safe_int(item.get("house_cnt")),
            }
        except Exception as e:
            logger.error(f"주택 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None
    
    def _convert_company_data(self, item: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
        """SGIS 사업체 통계 데이터를 DB 모델 형태로 변환"""
        try:
            return {
                "year": year,
                "adm_cd": item.get("adm_cd"),
                "adm_nm": item.get("adm_nm"),
                "company_cnt": self._safe_int(item.get("company_cnt")),
                "employee_cnt": self._safe_int(item.get("employee_cnt")),
            }
        except Exception as e:
            logger.error(f"사업체 데이터 변환 실패: {str(e)}, 데이터: {item}")
            return None
    
    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """안전한 정수 변환"""
        if value is None or value == "":
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """안전한 실수 변환"""
        if value is None or value == "":
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
        print("데이터 초기화가 완료되었습니다.")
    except Exception as e:
        print(f"데이터 초기화 실패: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())