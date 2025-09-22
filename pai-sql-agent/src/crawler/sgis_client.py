"""
SGIS API 클라이언트
통계청 통계지리정보서비스 SGIS API 호출을 담당하는 클라이언트 모듈
Docker Compose 환경변수와 통합 설정 지원
"""
import asyncio
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import httpx
from src.agent.settings import get_settings


class SGISDataType(Enum):
    """SGIS 데이터 타입"""
    POPULATION = "population"
    SEARCH_POPULATION = "searchpopulation"  # 추가
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


class SGISClient:
    """
    SGIS API 클라이언트
    Docker Compose 환경변수 기반 설정 지원
    """
    
    def __init__(self, service_id: Optional[str] = None, security_key: Optional[str] = None):
        """
        SGIS 클라이언트 초기화
        
        Args:
            service_id: SGIS 서비스 ID (None이면 환경변수에서 로드)
            security_key: SGIS 보안 키 (None이면 환경변수에서 로드)
        """
        # 설정에서 SGIS 정보 가져오기 (Docker 환경변수 포함)
        settings = get_settings()
        
        # 매개변수가 제공되면 사용, 아니면 환경변수에서 로드
        self.service_id = service_id or settings.sgis_service_id
        self.security_key = security_key or settings.sgis_security_key
        self.base_url = settings.sgis_base_url
        
        # 설정 검증
        if not self.service_id or not self.security_key:
            raise ValueError(
                "SGIS API 설정이 필요합니다. "
                "환경변수 SGIS_SERVICE_ID, SGIS_SECURITY_KEY를 설정하거나 "
                "생성자 매개변수로 전달하세요."
            )
        
        # HTTP 클라이언트 초기화
        self._client = httpx.AsyncClient(timeout=30.0)
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
    
    async def close(self):
        """클라이언트 정리"""
        if self._client:
            await self._client.aclose()
    
    async def authenticate(self) -> bool:
        """
        SGIS API 인증 토큰 획득
        Docker 환경변수의 service_id, security_key 사용
        
        Returns:
            bool: 인증 성공 여부
        """
        try:
            # 기존 토큰이 유효한지 확인
            if self._access_token and self._token_expires_at:
                if datetime.now() < self._token_expires_at:
                    return True
            
            # 새 토큰 요청
            auth_url = f"{self.base_url}/auth/authentication.json"
            params = {
                "consumer_key": self.service_id,
                "consumer_secret": self.security_key
            }
            
            response = await self._client.get(auth_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("errCd") == "0":
                # 인증 성공
                result = data.get("result", {})
                self._access_token = result.get("accessToken")
                
                # 토큰 만료 시간 설정 (1시간)
                self._token_expires_at = datetime.now() + timedelta(hours=1)
                
                return True
            else:
                # 인증 실패
                error_msg = data.get("errMsg", "Unknown authentication error")
                raise Exception(f"SGIS 인증 실패: {error_msg}")
                
        except Exception as e:
            print(f"SGIS 인증 오류: {e}")
            return False
    
    async def get_population_data(
        self, 
        year: int, 
        adm_cd: str, 
        low_search: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        인구 데이터 조회
        
        Args:
            year: 조회 연도
            adm_cd: 행정구역 코드
            low_search: 하위 행정구역 포함 여부 (0: 미포함, 1: 포함)
            
        Returns:
            Dict[str, Any]: 인구 데이터 또는 None
        """
        # 인증 확인
        if not await self.authenticate():
            return None
        
        try:
            # API 요청
            api_url = f"{self.base_url}/stats/population.json"
            params = {
                "accessToken": self._access_token,
                "year": year,
                "adm_cd": adm_cd,
                "low_search": low_search
            }
            
            response = await self._client.get(api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("errCd") == "0":
                return data
            else:
                error_msg = data.get("errMsg", "Unknown API error")
                print(f"SGIS API 오류: {error_msg}")
                return None
                
        except Exception as e:
            print(f"인구 데이터 조회 오류: {e}")
            return None
    
    async def get_household_data(
        self, 
        year: int, 
        adm_cd: str, 
        low_search: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        가구 데이터 조회
        
        Args:
            year: 조회 연도
            adm_cd: 행정구역 코드
            low_search: 하위 행정구역 포함 여부
            
        Returns:
            Dict[str, Any]: 가구 데이터 또는 None
        """
        if not await self.authenticate():
            return None
        
        try:
            api_url = f"{self.base_url}/stats/household.json"
            params = {
                "accessToken": self._access_token,
                "year": year,
                "adm_cd": adm_cd,
                "low_search": low_search
            }
            
            response = await self._client.get(api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("errCd") == "0":
                return data
            else:
                error_msg = data.get("errMsg", "Unknown API error")
                print(f"SGIS API 오류: {error_msg}")
                return None
                
        except Exception as e:
            print(f"가구 데이터 조회 오류: {e}")
            return None
    
    async def get_company_data(
        self, 
        year: int, 
        adm_cd: str, 
        low_search: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        사업체 데이터 조회
        
        Args:
            year: 조회 연도
            adm_cd: 행정구역 코드
            low_search: 하위 행정구역 포함 여부
            
        Returns:
            Dict[str, Any]: 사업체 데이터 또는 None
        """
        if not await self.authenticate():
            return None
        
        try:
            api_url = f"{self.base_url}/stats/company.json"
            params = {
                "accessToken": self._access_token,
                "year": year,
                "adm_cd": adm_cd,
                "low_search": low_search
            }
            
            response = await self._client.get(api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("errCd") == "0":
                return data
            else:
                error_msg = data.get("errMsg", "Unknown API error")
                print(f"SGIS API 오류: {error_msg}")
                return None
                
        except Exception as e:
            print(f"사업체 데이터 조회 오류: {e}")
            return None


# 헬퍼 함수들
async def create_sgis_client() -> SGISClient:
    """
    SGIS 클라이언트 생성 (환경변수 기반)
    Docker Compose 환경변수 자동 로드
    
    Returns:
        SGISClient: 설정된 SGIS 클라이언트
        
    Raises:
        ValueError: SGIS 설정이 없는 경우
    """
    return SGISClient()  # 환경변수에서 자동 로드


async def test_sgis_connection() -> bool:
    """
    SGIS API 연결 테스트
    
    Returns:
        bool: 연결 성공 여부
    """
    try:
        async with create_sgis_client() as client:
            return await client.authenticate()
    except Exception:
        return False


def is_sgis_configured() -> bool:
    """
    SGIS API 설정 여부 확인
    
    Returns:
        bool: 설정 완료 여부
    """
    try:
        settings = get_settings()
        return settings.sgis_configured
    except Exception:
        return False