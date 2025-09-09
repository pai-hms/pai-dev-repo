"""
SGIS API 클라이언트
데이터와 로직의 일체화 원칙에 따라 SGIS API 관련 데이터와 로직을 함께 관리
"""
import asyncio
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta  # timedelta 추가
from dataclasses import dataclass
from enum import Enum

import httpx
from src.config.settings import get_settings


class SGISDataType(Enum):
    """SGIS 데이터 타입"""
    POPULATION = "population"
    HOUSEHOLD = "household"
    HOUSE = "house"
    COMPANY = "company"
    INDUSTRY_CODE = "industrycode"
    FARM_HOUSEHOLD = "farmhousehold"
    FORESTRY_HOUSEHOLD = "forestryhousehold"
    FISHERY_HOUSEHOLD = "fisheryhousehold"
    HOUSEHOLD_MEMBER = "householdmember"


@dataclass
class SGISResponse:
    """SGIS API 응답 데이터"""
    id: str
    result: List[Dict[str, Any]]
    err_msg: str
    err_cd: int
    tr_id: str
    
    @property
    def is_success(self) -> bool:
        """응답 성공 여부"""
        return self.err_cd == 0
    
    @property
    def error_message(self) -> Optional[str]:
        """에러 메시지 반환"""
        return self.err_msg if not self.is_success else None

# src/crawler/sgis_client.py
class SGISClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.sgis_base_url
        self.service_id = self.settings.sgis_service_id
        self.security_key = self.settings.sgis_security_key
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # SGIS API 엔드포인트 정의
        self.endpoints = {
            SGISDataType.POPULATION: "/stats/population.json",
            SGISDataType.HOUSEHOLD: "/stats/household.json", 
            SGISDataType.HOUSE: "/stats/house.json",
            SGISDataType.COMPANY: "/stats/company.json",
            SGISDataType.FARM_HOUSEHOLD: "/stats/farmhousehold.json",
            SGISDataType.FORESTRY_HOUSEHOLD: "/stats/forestryhousehold.json",
            SGISDataType.FISHERY_HOUSEHOLD: "/stats/fisheryhousehold.json",
            SGISDataType.HOUSEHOLD_MEMBER: "/stats/householdmember.json"
        }

    async def _get_access_token(self) -> str:
        """액세스 토큰 획득 - SGIS 표준 방식"""
        # 토큰이 유효한지 확인
        if (self._access_token and 
            self._token_expires_at and 
            datetime.now() < self._token_expires_at):
            return self._access_token
        
        # SGIS 표준 인증 방식 (GET 방식으로 변경)
        auth_url = f"{self.base_url}/auth/authentication.json"
        auth_params = {  # data → params로 변경
            "consumer_key": self.service_id,
            "consumer_secret": self.security_key
        }
        
        async with httpx.AsyncClient(timeout=self.settings.api_timeout) as client:
            response = await client.get(auth_url, params=auth_params)  # POST → GET으로 변경
            response.raise_for_status()
            
            auth_result = response.json()
            if auth_result.get("errCd") != 0:
                raise ValueError(f"인증 실패: {auth_result.get('errMsg')}")
            
            self._access_token = auth_result["result"]["accessToken"]
            # 토큰 만료 시간을 4시간으로 설정 (여유를 두고 3시간 50분)
            self._token_expires_at = datetime.now() + timedelta(hours=3, minutes=50)
            
            return self._access_token
    
    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Union[str, int]]
    ) -> SGISResponse:
        """API 요청 실행"""
        access_token = await self._get_access_token()
        
        request_params = {  # data → params로 변경
            "accessToken": access_token,
            **params
        }
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.settings.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.settings.api_timeout) as client:
                    response = await client.get(url, params=request_params)  # POST → GET으로 변경
                    response.raise_for_status()
                    
                    result = response.json()
                    return SGISResponse(
                        id=result.get("id", ""),
                        result=result.get("result", []),
                        err_msg=result.get("errMsg", ""),
                        err_cd=result.get("errCd", -1),
                        tr_id=result.get("trId", "")
                    )
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt == self.settings.max_retries - 1:
                    raise ValueError(f"API 요청 실패: {str(e)}")
                
                # 재시도 전 대기
                await asyncio.sleep(2 ** attempt)
        
        raise ValueError("최대 재시도 횟수 초과")
    
    async def get_population_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 1
    ) -> SGISResponse:
        """인구 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.POPULATION],
            params
        )
    
    async def get_household_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 1
    ) -> SGISResponse:
        """가구 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.HOUSEHOLD],
            params
        )
    
    async def get_house_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 1
    ) -> SGISResponse:
        """주택 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.HOUSE],
            params
        )
    
    async def get_company_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 1
    ) -> SGISResponse:
        """사업체 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.COMPANY],
            params
        )
    
    async def get_farm_household_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 0
    ) -> SGISResponse:
        """농가 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.FARM_HOUSEHOLD],
            params
        )
    
    async def get_forestry_household_stats(
        self,
        year: int,
        adm_cd: Optional[str] = None,
        low_search: int = 0
    ) -> SGISResponse:
        """임가 통계 조회"""
        params = {
            "year": year,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.FORESTRY_HOUSEHOLD],
            params
        )
    
    async def get_fishery_household_stats(
        self,
        year: int,
        oga_div: int = 0,
        adm_cd: Optional[str] = None,
        low_search: int = 0
    ) -> SGISResponse:
        """어가 통계 조회"""
        params = {
            "year": year,
            "oga_div": oga_div,
            "low_search": low_search
        }
        if adm_cd:
            params["adm_cd"] = adm_cd
        
        return await self._make_request(
            self.endpoints[SGISDataType.FISHERY_HOUSEHOLD],
            params
        )
    
    async def get_household_member_stats(
        self,
        year: int,
        data_type: int,
        adm_cd: Optional[str] = None,
        low_search: int = 0,
        gender: Optional[int] = None,
        age_from: Optional[int] = None,
        age_to: Optional[int] = None
    ) -> SGISResponse:
        """가구원 통계 조회"""
        params = {
            "year": year,
            "data_type": data_type,
            "low_search": low_search
        }
        
        if adm_cd:
            params["adm_cd"] = adm_cd
        if gender is not None:
            params["gender"] = gender
        if age_from is not None:
            params["age_from"] = age_from
        if age_to is not None:
            params["age_to"] = age_to
        
        return await self._make_request(
            self.endpoints[SGISDataType.HOUSEHOLD_MEMBER],
            params
        )
    
    async def get_all_administrative_divisions(self) -> List[Dict[str, str]]:
        """모든 행정구역 코드 조회"""
        # 시도 목록 조회
        sido_response = await self.get_population_stats(year=2023, low_search=1)
        
        if not sido_response.is_success:
            raise ValueError(f"시도 목록 조회 실패: {sido_response.error_message}")
        
        all_divisions = []
        
        for sido in sido_response.result:
            sido_cd = sido.get("adm_cd")
            if not sido_cd or len(sido_cd) != 2:
                continue
            
            all_divisions.append({
                "adm_cd": sido_cd,
                "adm_nm": sido.get("adm_nm", ""),
                "level": "sido"
            })
            
            # 시군구 목록 조회
            try:
                sigungu_response = await self.get_population_stats(
                    year=2023, 
                    adm_cd=sido_cd, 
                    low_search=1
                )
                
                if sigungu_response.is_success:
                    for sigungu in sigungu_response.result:
                        sigungu_cd = sigungu.get("adm_cd")
                        if sigungu_cd and len(sigungu_cd) == 5:
                            all_divisions.append({
                                "adm_cd": sigungu_cd,
                                "adm_nm": sigungu.get("adm_nm", ""),
                                "level": "sigungu"
                            })
                
                # API 호출 간격 조정
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"시군구 조회 실패 (시도: {sido_cd}): {str(e)}")
                continue
        
        return all_divisions