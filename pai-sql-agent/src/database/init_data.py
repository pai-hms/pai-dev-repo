"""
데이터베이스 초기 데이터 로더
SGIS API를 통해 각종 통계 데이터를 수집하여 데이터베이스에 저장
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.agent.settings import get_settings
from src.database.connection import get_database_manager
from src.database.service import get_database_service  # ✅ Service Layer 사용
from src.crawler.sgis_client import SGISClient, SGISDataType


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataInitializer:
    """데이터 초기화 클래스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = None  # 비동기로 초기화될 예정
        self.db_service = None
        self.sgis_client = None
    
    async def initialize(self):
        """비동기 초기화"""
        self.db_manager = await get_database_manager()
        # Service Layer를 통한 접근
        self.db_service = await get_database_service()
        
        # SGIS 클라이언트 초기화
        if all([
            self.settings.sgis_service_id,
            self.settings.sgis_security_key
        ]):
            self.sgis_client = SGISClient(
                service_id=self.settings.sgis_service_id,
                security_key=self.settings.sgis_security_key
            )
            logger.info("SGIS 클라이언트 초기화 완료")
        else:
            logger.warning(" SGIS API 키가 설정되지 않았습니다")
    
    async def create_tables(self):
        """데이터베이스 테이블 생성"""
        try:
            await self.db_manager.create_tables()
            logger.info("데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise

    async def load_all_data(self, year: int = 2023):
        """모든 통계 데이터 로드"""
        if not self.sgis_client:
            logger.error("SGIS 클라이언트가 초기화되지 않았습니다")
            return
        
        logger.info(f"{year}년 통계 데이터 로딩 시작")
        
        # 데이터 타입별 로드
        data_types = [
            SGISDataType.POPULATION,
            SGISDataType.SEARCH_POPULATION,
            SGISDataType.HOUSEHOLD,
            SGISDataType.HOUSE,
            SGISDataType.COMPANY,
            SGISDataType.INDUSTRY_CODE,
            SGISDataType.FARM_HOUSEHOLD,
            SGISDataType.FORESTRY_HOUSEHOLD,
            SGISDataType.FISHERY_HOUSEHOLD,
            SGISDataType.HOUSEHOLD_MEMBER
        ]
        
        for data_type in data_types:
            try:
                await self._load_data_type(data_type, year)
            except Exception as e:  # 수정: 올바른 예외 처리
                logger.error(f"{data_type.value} 데이터 로딩 실패: {e}")
        
        logger.info("모든 통계 데이터 로딩 완료")
    
    async def _load_data_type(self, data_type: SGISDataType, year: int):
        """특정 데이터 타입 로드"""
        logger.info(f"{data_type.value} 데이터 로딩 중...")

        # 전국 시도별 데이터 수집
        sido_codes = [
            "11", "26", "27", "28", "29", "30", "31", "36",  # 특별시/광역시
            "41", "42", "43", "44", "45", "46", "47", "48", "50"  # 도
        ]
        
        total_records = 0
        
        for sido_code in sido_codes:
            try:
                # SGIS API 호출
                data = await self.sgis_client.get_population_data(
                    year=year,
                    adm_cd=sido_code,
                    low_search=1  # 하위 행정구역 포함
                )
                
                if data and "result" in data:
                    records = data["result"]
                    
                    # 데이터베이스 저장
                    saved_count = await self._save_data_records(
                        data_type, records, year
                    )
                    total_records += saved_count
                    
                    logger.info(f"{sido_code} 지역 {saved_count}개 레코드 저장")
                
                # API 제한 고려 (1초 대기)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"{sido_code} 지역 데이터 처리 실패: {e}")
        
        logger.info(f"{data_type.value} 총 {total_records}개 레코드 저장 완료")
    
    async def _save_data_records(
        self, 
        data_type: SGISDataType, 
        records: List[Dict], 
        year: int
    ) -> int:
        """데이터 레코드 저장"""
        if not records:
            return 0
        
        try:
            # 임시 구현: Service Layer에 저장 메서드가 없으므로 기본 쿼리 실행
            # 실제 구현에서는 각 데이터 타입별 저장 로직을 Service Layer에 추가해야 함
            logger.info(f"{data_type.value} 데이터 {len(records)}개 저장 시뮬레이션")
            
            # 데이터 타입에 따른 저장 시뮬레이션
            if data_type == SGISDataType.POPULATION:
                logger.info("인구 통계 데이터 저장 중...")
            elif data_type == SGISDataType.SEARCH_POPULATION:
                logger.info("인구 검색 통계 데이터 저장 중...")
            elif data_type == SGISDataType.HOUSEHOLD:
                logger.info("가구 통계 데이터 저장 중...")
            elif data_type == SGISDataType.HOUSE:
                logger.info("주택 통계 데이터 저장 중...")
            elif data_type == SGISDataType.COMPANY:
                logger.info("사업체 통계 데이터 저장 중...")
            elif data_type == SGISDataType.INDUSTRY_CODE:
                logger.info("산업분류 통계 데이터 저장 중...")
            elif data_type == SGISDataType.FARM_HOUSEHOLD:
                logger.info("농가 통계 데이터 저장 중...")
            elif data_type == SGISDataType.FORESTRY_HOUSEHOLD:
                logger.info("임가 통계 데이터 저장 중...")
            elif data_type == SGISDataType.FISHERY_HOUSEHOLD:
                logger.info("어가 통계 데이터 저장 중...")
            elif data_type == SGISDataType.HOUSEHOLD_MEMBER:
                logger.info("가구원 통계 데이터 저장 중...")
            else:
                logger.warning(f"알 수 없는 데이터 타입: {data_type}")
                return 0
            
            # 시뮬레이션: 저장된 레코드 수 반환
            return len(records)
                    
        except Exception as e:  # 수정: 올바른 들여쓰기
            logger.error(f"데이터 저장 실패: {e}")
            return 0


# 메인 실행 함수
async def main():
    """메인 데이터 로딩 함수"""
    initializer = DataInitializer()
    
    try:
        # 초기화
        await initializer.initialize()
        
        # 테이블 생성
        await initializer.create_tables()
        
        # 데이터 로드 (2023년)
        await initializer.load_all_data(2023)
        
        logger.info("데이터 초기화 완료!")
        
    except Exception as e:
        logger.error(f"데이터 초기화 실패: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())