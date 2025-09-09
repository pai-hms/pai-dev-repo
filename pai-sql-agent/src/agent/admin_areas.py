"""
행정구역 정보 관리 모듈
SGIS API에서 행정구역 데이터를 가져와서 프롬프트에 포함할 완전한 목록 생성
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from src.config.settings import get_settings
from src.crawler.sgis_client import SGISClient
from src.database.connection import get_database_manager
from src.database.repository import DatabaseService

logger = logging.getLogger(__name__)


class AdminAreaManager:
    """행정구역 정보 관리 클래스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.sgis_client = SGISClient()
        self.db_manager = get_database_manager()
        self._cached_areas: Optional[Dict[str, str]] = None
        self._cache_updated_at: Optional[datetime] = None
        self._cache_duration = timedelta(hours=24)  # 24시간 캐시
    
    async def get_all_administrative_areas(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        모든 행정구역 정보 조회 (캐시 지원)
        
        Args:
            force_refresh: 강제 새로고침 여부
            
        Returns:
            {행정구역코드: 행정구역명} 딕셔너리
        """
        # 캐시 확인
        if not force_refresh and self._is_cache_valid():
            logger.info("캐시된 행정구역 데이터 사용")
            return self._cached_areas
        
        logger.info("SGIS API에서 행정구역 데이터 새로 조회")
        
        try:
            # 데이터베이스에서 최신 행정구역 정보 조회
            areas = await self._get_areas_from_database()
            
            if not areas:
                # 데이터베이스에 데이터가 없으면 SGIS API에서 직접 조회
                logger.warning("데이터베이스에 행정구역 정보가 없음. SGIS API에서 직접 조회")
                areas = await self._get_areas_from_sgis()
            
            # 캐시 업데이트
            self._cached_areas = areas
            self._cache_updated_at = datetime.now()
            
            logger.info(f"행정구역 {len(areas)}개 조회 완료")
            return areas
            
        except Exception as e:
            logger.error(f"행정구역 정보 조회 실패: {str(e)}")
            # 캐시가 있으면 그것을 사용
            if self._cached_areas:
                logger.warning("오류 발생, 캐시된 데이터 사용")
                return self._cached_areas
            raise
    
    async def _get_areas_from_database(self) -> Dict[str, str]:
        """데이터베이스에서 행정구역 정보 조회"""
        try:
            query = """
            SELECT DISTINCT adm_cd, adm_nm 
            FROM population_stats 
            WHERE year = 2023 
            AND adm_cd IS NOT NULL 
            AND adm_nm IS NOT NULL
            ORDER BY adm_cd
            """
            
            async with self.db_manager.get_async_session() as session:
                db_service = DatabaseService(session)
                results = await db_service.execute_raw_query(query)
            
            areas = {}
            for result in results:
                adm_cd = result.get('adm_cd')
                adm_nm = result.get('adm_nm')
                if adm_cd and adm_nm:
                    areas[adm_cd] = adm_nm
            
            logger.info(f"데이터베이스에서 {len(areas)}개 행정구역 조회")
            return areas
            
        except Exception as e:
            logger.error(f"데이터베이스 행정구역 조회 실패: {str(e)}")
            return {}
    
    async def _get_areas_from_sgis(self) -> Dict[str, str]:
        """SGIS API에서 직접 행정구역 정보 조회"""
        try:
            divisions = await self.sgis_client.get_all_administrative_divisions()
            
            areas = {}
            for division in divisions:
                adm_cd = division.get('adm_cd')
                adm_nm = division.get('adm_nm')
                if adm_cd and adm_nm:
                    areas[adm_cd] = adm_nm
            
            logger.info(f"SGIS API에서 {len(areas)}개 행정구역 조회")
            return areas
            
        except Exception as e:
            logger.error(f"SGIS API 행정구역 조회 실패: {str(e)}")
            return {}
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if not self._cached_areas or not self._cache_updated_at:
            return False
        
        return datetime.now() - self._cache_updated_at < self._cache_duration
    
    def generate_area_code_info(self, areas: Dict[str, str]) -> str:
        """
        프롬프트에 포함할 행정구역 정보 문자열 생성
        
        Args:
            areas: {행정구역코드: 행정구역명} 딕셔너리
            
        Returns:
            포맷팅된 행정구역 정보 문자열
        """
        if not areas:
            return "### 행정구역 정보\n- 행정구역 정보를 불러올 수 없습니다.\n"
        
        # 시도, 시군구, 읍면동 별로 분류
        sido_areas = {}      # 2자리 코드
        sigungu_areas = {}   # 5자리 코드  
        dong_areas = {}      # 8자리 코드
        
        for code, name in areas.items():
            if len(code) == 2:
                sido_areas[code] = name
            elif len(code) == 5:
                sigungu_areas[code] = name
            elif len(code) == 8:
                dong_areas[code] = name
        
        # 문자열 생성
        lines = ["### 행정구역 정보 (완전 목록)", ""]
        
        # 1. 시도 (광역자치단체)
        if sido_areas:
            lines.append("#### 1. 시도 (광역자치단체)")
            for code in sorted(sido_areas.keys()):
                lines.append(f"- {code}: {sido_areas[code]}")
            lines.append("")
        
        # 2. 시군구 정보 (너무 많으면 주요 지역만)
        if sigungu_areas:
            lines.append("#### 2. 시군구 (기초자치단체)")
            lines.append("주요 시군구 코드:")
            
            # 주요 지역 우선 표시
            major_cities = {
                '11110': '종로구', '11140': '중구', '11170': '용산구',  # 서울
                '26110': '중구', '26140': '서구', '26170': '사하구',    # 부산
                '27110': '중구', '27140': '동구', '27170': '서구',     # 대구
                '28110': '중구', '28140': '동구', '28177': '연수구',    # 인천
                '47110': '포항시 남구', '47113': '포항시 북구',        # 경북
            }
            
            # 주요 도시 먼저 표시
            for code, name in major_cities.items():
                if code in sigungu_areas:
                    lines.append(f"- {code}: {sigungu_areas[code]}")
            
            lines.append(f"※ 총 {len(sigungu_areas)}개 시군구 (전체 목록은 데이터베이스 조회 가능)")
            lines.append("")
        
        # 3. 읍면동 정보 (통계만)
        if dong_areas:
            lines.append("#### 3. 읍면동")
            lines.append(f"- 총 {len(dong_areas)}개 읍면동 등록")
            lines.append("- 8자리 코드로 구성 (예: 11110101)")
            lines.append("- 구체적인 읍면동 정보는 search_administrative_area 도구 사용")
            lines.append("")
        
        # 4. 코드 체계 설명
        lines.extend([
            "#### 행정구역코드 체계",
            "- 2자리: 시도 (광역자치단체)",
            "- 5자리: 시군구 (기초자치단체)", 
            "- 8자리: 읍면동 (행정동/법정동)",
            "",
            "#### 검색 방법",
            "- 행정구역명으로 검색: search_administrative_area('지역명') 도구 사용",
            "- 예: search_administrative_area('포항') → 47110 (포항시)"
        ])
        
        return "\n".join(lines)
    
    async def save_areas_to_file(self, areas: Dict[str, str], file_path: str = "admin_areas.json"):
        """행정구역 정보를 파일로 저장 (백업용)"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(areas, f, ensure_ascii=False, indent=2)
            logger.info(f"행정구역 정보 {len(areas)}개를 {file_path}에 저장")
        except Exception as e:
            logger.error(f"행정구역 정보 파일 저장 실패: {str(e)}")


# 싱글톤 인스턴스
_admin_area_manager: Optional[AdminAreaManager] = None


def get_admin_area_manager() -> AdminAreaManager:
    """AdminAreaManager 싱글톤 인스턴스 반환"""
    global _admin_area_manager
    if _admin_area_manager is None:
        _admin_area_manager = AdminAreaManager()
    return _admin_area_manager


async def get_comprehensive_area_info() -> str:
    """
    프롬프트에 포함할 완전한 행정구역 정보 반환
    
    Returns:
        포맷팅된 행정구역 정보 문자열
    """
    try:
        manager = get_admin_area_manager()
        areas = await manager.get_all_administrative_areas()
        return manager.generate_area_code_info(areas)
    except Exception as e:
        logger.error(f"완전한 행정구역 정보 생성 실패: {str(e)}")
        return "### 행정구역 정보\n- 행정구역 정보 로딩 중 오류가 발생했습니다.\n"


async def refresh_area_cache():
    """행정구역 캐시 강제 새로고침"""
    try:
        manager = get_admin_area_manager()
        areas = await manager.get_all_administrative_areas(force_refresh=True)
        logger.info(f"행정구역 캐시 새로고침 완료: {len(areas)}개")
        return areas
    except Exception as e:
        logger.error(f"행정구역 캐시 새로고침 실패: {str(e)}")
        return {}


if __name__ == "__main__":
    # 테스트용
    async def main():
        manager = get_admin_area_manager()
        areas = await manager.get_all_administrative_areas()
        info = manager.generate_area_code_info(areas)
        print(info)
        
        # 파일로 저장
        await manager.save_areas_to_file(areas)
    
    asyncio.run(main())
