"""SGIS API client for census data crawling."""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from pydantic import BaseModel

from src.config import settings


class SGISAuthResponse(BaseModel):
    """SGIS authentication response model."""
    result: Dict[str, Any]
    errMsg: Optional[str] = None
    errCd: Optional[int] = None


class SGISDataResponse(BaseModel):
    """SGIS data response model."""
    result: List[Dict[str, Any]]
    errMsg: Optional[str] = None
    errCd: Optional[int] = None


class SGISClient:
    """SGIS API client following KISS principle and data sovereignty."""
    
    BASE_URL = "https://sgis.kostat.go.kr/OpenAPI3"
    
    def __init__(self):
        self.api_key = settings.sgis_api_key
        self.secret_key = settings.sgis_secret_key
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp for API authentication."""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, timestamp: str) -> str:
        """Generate signature for API authentication."""
        message = f"{self.api_key}{self.secret_key}{timestamp}"
        return hashlib.md5(message.encode()).hexdigest()
    
    async def _authenticate(self) -> str:
        """Authenticate with SGIS API and get access token."""
        if not self.api_key or not self.secret_key:
            raise ValueError("SGIS API key and secret key are required")
        
        # Check if token is still valid
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at):
            return self.access_token
        
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(timestamp)
        
        auth_url = f"{self.BASE_URL}/auth/authentication.json"
        params = {
            "consumer_key": self.api_key,
            "consumer_secret": self.secret_key,
            "timestamp": timestamp,
            "signature": signature,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(auth_url, params=params)
        response.raise_for_status()
        
        auth_data = SGISAuthResponse(**response.json())
        
        if auth_data.errCd:
            raise Exception(f"SGIS Auth Error: {auth_data.errMsg}")
        
        self.access_token = auth_data.result.get("accessToken")
        # Token expires in 1 hour, set expiry to 50 minutes for safety
        self.token_expires_at = datetime.now().replace(
            minute=datetime.now().minute + 50
        )
        
        return self.access_token
    
    async def get_population_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"  # Pohang city code
    ) -> List[Dict[str, Any]]:
        """Get population census data from SGIS API."""
        access_token = await self._authenticate()
        
        pop_url = f"{self.BASE_URL}/stats/population.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(pop_url, params=params)
        response.raise_for_status()
        
        pop_data = SGISDataResponse(**response.json())
        
        if pop_data.errCd:
            raise Exception(f"SGIS Data Error: {pop_data.errMsg}")
        
        return pop_data.result
    
    async def search_population_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130",
        search_type: str = "1"  # 1: 행정구역별, 2: 격자별
    ) -> List[Dict[str, Any]]:
        """Search population data with various criteria."""
        access_token = await self._authenticate()
        
        search_url = f"{self.BASE_URL}/stats/searchpopulation.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
            "search_type": search_type,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(search_url, params=params)
        response.raise_for_status()
        
        search_data = SGISDataResponse(**response.json())
        
        if search_data.errCd:
            raise Exception(f"SGIS Data Error: {search_data.errMsg}")
        
        return search_data.result
    
    async def get_household_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get household census data from SGIS API."""
        access_token = await self._authenticate()
        
        household_url = f"{self.BASE_URL}/stats/household.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(household_url, params=params)
        response.raise_for_status()
        
        household_data = SGISDataResponse(**response.json())
        
        if household_data.errCd:
            raise Exception(f"SGIS Data Error: {household_data.errMsg}")
        
        return household_data.result
    
    async def get_housing_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get housing census data from SGIS API."""
        access_token = await self._authenticate()
        
        house_url = f"{self.BASE_URL}/stats/house.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(house_url, params=params)
        response.raise_for_status()
        
        house_data = SGISDataResponse(**response.json())
        
        if house_data.errCd:
            raise Exception(f"SGIS Data Error: {house_data.errMsg}")
        
        return house_data.result
    
    async def get_company_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get company/business census data from SGIS API."""
        access_token = await self._authenticate()
        
        company_url = f"{self.BASE_URL}/stats/company.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(company_url, params=params)
        response.raise_for_status()
        
        company_data = SGISDataResponse(**response.json())
        
        if company_data.errCd:
            raise Exception(f"SGIS Data Error: {company_data.errMsg}")
        
        return company_data.result
    
    async def get_industry_code_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130",
        industry_cd: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get industry classification data from SGIS API."""
        access_token = await self._authenticate()
        
        industry_url = f"{self.BASE_URL}/stats/industrycode.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if industry_cd:
            params["industry_cd"] = industry_cd
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(industry_url, params=params)
        response.raise_for_status()
        
        industry_data = SGISDataResponse(**response.json())
        
        if industry_data.errCd:
            raise Exception(f"SGIS Data Error: {industry_data.errMsg}")
        
        return industry_data.result
    
    async def get_farm_household_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get agricultural household data from SGIS API."""
        access_token = await self._authenticate()
        
        farm_url = f"{self.BASE_URL}/stats/farmhousehold.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(farm_url, params=params)
        response.raise_for_status()
        
        farm_data = SGISDataResponse(**response.json())
        
        if farm_data.errCd:
            raise Exception(f"SGIS Data Error: {farm_data.errMsg}")
        
        return farm_data.result
    
    async def get_forestry_household_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get forestry household data from SGIS API."""
        access_token = await self._authenticate()
        
        forestry_url = f"{self.BASE_URL}/stats/forestryhousehold.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(forestry_url, params=params)
        response.raise_for_status()
        
        forestry_data = SGISDataResponse(**response.json())
        
        if forestry_data.errCd:
            raise Exception(f"SGIS Data Error: {forestry_data.errMsg}")
        
        return forestry_data.result
    
    async def get_fishery_household_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get fishery household data from SGIS API."""
        access_token = await self._authenticate()
        
        fishery_url = f"{self.BASE_URL}/stats/fisheryhousehold.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(fishery_url, params=params)
        response.raise_for_status()
        
        fishery_data = SGISDataResponse(**response.json())
        
        if fishery_data.errCd:
            raise Exception(f"SGIS Data Error: {fishery_data.errMsg}")
        
        return fishery_data.result
    
    async def get_household_member_data(
        self, 
        year: int = 2023, 
        area_cd: str = "47130"
    ) -> List[Dict[str, Any]]:
        """Get household member data from SGIS API."""
        access_token = await self._authenticate()
        
        member_url = f"{self.BASE_URL}/stats/householdmember.json"
        params = {
            "accessToken": access_token,
            "year": str(year),
            "area_cd": area_cd,
        }
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self._client.get(member_url, params=params)
        response.raise_for_status()
        
        member_data = SGISDataResponse(**response.json())
        
        if member_data.errCd:
            raise Exception(f"SGIS Data Error: {member_data.errMsg}")
        
        return member_data.result


class DataCrawler:
    """Data crawler for comprehensive SGIS census data with data sovereignty principle."""
    
    def __init__(self):
        self.sgis_client = SGISClient()
    
    async def crawl_comprehensive_census_data(self, year: int = 2023) -> Dict[str, List[Dict[str, Any]]]:
        """Crawl all available census data for Pohang city."""
        async with self.sgis_client as client:
            # Crawl all types of census data concurrently for maximum efficiency
            tasks = {
                "population": client.get_population_data(year),
                "population_search": client.search_population_data(year),
                "household": client.get_household_data(year),
                "housing": client.get_housing_data(year),
                "company": client.get_company_data(year),
                "industry": client.get_industry_code_data(year),
                "agriculture": client.get_farm_household_data(year),
                "forestry": client.get_forestry_household_data(year),
                "fishery": client.get_fishery_household_data(year),
                "household_members": client.get_household_member_data(year),
            }
            
            # Execute all tasks concurrently
            results = {}
            for key, task in tasks.items():
                try:
                    results[key] = await task
                except Exception as e:
                    print(f"⚠️  Failed to crawl {key} data: {e}")
                    results[key] = []
            
            return results
    
    async def crawl_pohang_census_data(self, year: int = 2023) -> Dict[str, List[Dict[str, Any]]]:
        """Backward compatibility method - crawl basic census data."""
        return await self.crawl_comprehensive_census_data(year)
    
    def transform_population_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS population data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_population": int(item.get("tot_ppltn", 0)),
                "male_population": int(item.get("male_ppltn", 0)),
                "female_population": int(item.get("fmle_ppltn", 0)),
                "household_count": int(item.get("household", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_household_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS household data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_households": int(item.get("tot_hshld", 0)),
                "ordinary_households": int(item.get("ord_hshld", 0)),
                "collective_households": int(item.get("col_hshld", 0)),
                "single_person_households": int(item.get("sgl_hshld", 0)),
                "multi_person_households": int(item.get("mlt_hshld", 0)),
                "average_household_size": float(item.get("avg_hshld_sz", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_housing_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS housing data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_houses": int(item.get("tot_house", 0)),
                "detached_houses": int(item.get("detached", 0)),
                "apartment_houses": int(item.get("apartment", 0)),
                "row_houses": int(item.get("row_house", 0)),
                "multi_unit_houses": int(item.get("multi_unit", 0)),
                "other_houses": int(item.get("other", 0)),
                "owned_houses": int(item.get("owned", 0)),
                "rented_houses": int(item.get("rented", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_company_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS company data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_companies": int(item.get("tot_company", 0)),
                "total_employees": int(item.get("tot_employee", 0)),
                "manufacturing_companies": int(item.get("manufacturing", 0)),
                "service_companies": int(item.get("service", 0)),
                "retail_companies": int(item.get("retail", 0)),
                "construction_companies": int(item.get("construction", 0)),
                "other_companies": int(item.get("other", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_industry_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS industry data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "industry_code": item.get("industry_cd"),
                "industry_name": item.get("industry_nm"),
                "company_count": int(item.get("company_cnt", 0)),
                "employee_count": int(item.get("employee_cnt", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_agricultural_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS agricultural household data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_farm_households": int(item.get("tot_farm_hshld", 0)),
                "full_time_farmers": int(item.get("full_time", 0)),
                "part_time_farmers": int(item.get("part_time", 0)),
                "farm_population": int(item.get("farm_pop", 0)),
                "cultivated_area": float(item.get("cult_area", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_forestry_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS forestry household data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_forestry_households": int(item.get("tot_forestry_hshld", 0)),
                "forestry_population": int(item.get("forestry_pop", 0)),
                "forest_area": float(item.get("forest_area", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_fishery_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS fishery household data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "total_fishery_households": int(item.get("tot_fishery_hshld", 0)),
                "fishery_population": int(item.get("fishery_pop", 0)),
                "fishing_boats": int(item.get("fishing_boats", 0)),
                "aquaculture_farms": int(item.get("aqua_farms", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
    
    def transform_household_member_data(
        self, raw_data: List[Dict[str, Any]], year: int
    ) -> List[Dict[str, Any]]:
        """Transform raw SGIS household member data to database format."""
        transformed_data = []
        
        for item in raw_data:
            transformed_item = {
                "year": year,
                "region_code": item.get("adm_cd"),
                "region_name": item.get("adm_nm"),
                "household_type": item.get("hshld_type", "unknown"),
                "member_count": int(item.get("member_cnt", 0)),
                "male_members": int(item.get("male_member", 0)),
                "female_members": int(item.get("female_member", 0)),
                "children_count": int(item.get("children", 0)),
                "elderly_count": int(item.get("elderly", 0)),
            }
            transformed_data.append(transformed_item)
        
        return transformed_data
