"""Database initialization script for Pohang City data."""

import asyncio
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.database.connection import async_engine, AsyncSessionLocal
from src.database.models import Base, BudgetCategory, BudgetItem, PopulationData
from src.crawler.sgis_client import DataCrawler


async def create_tables():
    """Create database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


async def init_budget_categories():
    """Initialize budget categories with sample data."""
    categories = [
        {"code": "100", "name": "일반공공행정", "parent_code": None, "level": 1},
        {"code": "110", "name": "일반행정", "parent_code": "100", "level": 2},
        {"code": "111", "name": "행정운영", "parent_code": "110", "level": 3},
        {"code": "200", "name": "공공질서및안전", "parent_code": None, "level": 1},
        {"code": "210", "name": "경찰", "parent_code": "200", "level": 2},
        {"code": "220", "name": "소방", "parent_code": "200", "level": 2},
        {"code": "300", "name": "교육", "parent_code": None, "level": 1},
        {"code": "310", "name": "유아및초중등교육", "parent_code": "300", "level": 2},
        {"code": "400", "name": "문화및관광", "parent_code": None, "level": 1},
        {"code": "410", "name": "문화예술", "parent_code": "400", "level": 2},
        {"code": "420", "name": "관광", "parent_code": "400", "level": 2},
        {"code": "500", "name": "환경보호", "parent_code": None, "level": 1},
        {"code": "510", "name": "상하수도", "parent_code": "500", "level": 2},
        {"code": "520", "name": "폐기물", "parent_code": "500", "level": 2},
        {"code": "600", "name": "사회복지", "parent_code": None, "level": 1},
        {"code": "610", "name": "기초생활보장", "parent_code": "600", "level": 2},
        {"code": "620", "name": "취약계층지원", "parent_code": "600", "level": 2},
        {"code": "700", "name": "보건", "parent_code": None, "level": 1},
        {"code": "710", "name": "보건의료", "parent_code": "700", "level": 2},
        {"code": "800", "name": "농림해양수산", "parent_code": None, "level": 1},
        {"code": "810", "name": "농업", "parent_code": "800", "level": 2},
        {"code": "820", "name": "해양수산", "parent_code": "800", "level": 2},
    ]
    
    async with AsyncSessionLocal() as session:
        for cat_data in categories:
            category = BudgetCategory(**cat_data)
            session.add(category)
        
        await session.commit()
    
    print(f"✅ Initialized {len(categories)} budget categories")


async def init_sample_budget_items():
    """Initialize sample budget items for 2023."""
    sample_items = [
        {
            "year": 2023,
            "category_code": "111",
            "item_name": "시청 운영비",
            "budget_amount": 15000000000,  # 150억
            "executed_amount": 12500000000,  # 125억
            "execution_rate": 83.33,
            "department": "기획예산실",
            "sub_department": "예산담당관",
            "description": "시청 기본 운영을 위한 예산",
        },
        {
            "year": 2023,
            "category_code": "220",
            "item_name": "소방서 운영 및 장비구입",
            "budget_amount": 8500000000,  # 85억
            "executed_amount": 8200000000,  # 82억
            "execution_rate": 96.47,
            "department": "소방본부",
            "sub_department": "소방행정과",
            "description": "소방안전 강화를 위한 운영비 및 장비구입비",
        },
        {
            "year": 2023,
            "category_code": "310",
            "item_name": "교육환경 개선사업",
            "budget_amount": 25000000000,  # 250억
            "executed_amount": 23800000000,  # 238억
            "execution_rate": 95.20,
            "department": "교육지원과",
            "sub_department": "교육시설담당",
            "description": "학교 시설 현대화 및 교육환경 개선",
        },
        {
            "year": 2023,
            "category_code": "420",
            "item_name": "포항 관광 활성화 사업",
            "budget_amount": 12000000000,  # 120억
            "executed_amount": 10800000000,  # 108억
            "execution_rate": 90.00,
            "department": "문화관광과",
            "sub_department": "관광진흥담당",
            "description": "포항 관광 인프라 구축 및 홍보사업",
        },
        {
            "year": 2023,
            "category_code": "510",
            "item_name": "상하수도 시설 확충",
            "budget_amount": 18000000000,  # 180억
            "executed_amount": 17100000000,  # 171억
            "execution_rate": 95.00,
            "department": "상하수도사업소",
            "sub_department": "시설관리과",
            "description": "노후 상하수도 시설 교체 및 확충",
        },
        {
            "year": 2023,
            "category_code": "620",
            "item_name": "취약계층 복지지원",
            "budget_amount": 30000000000,  # 300억
            "executed_amount": 29500000000,  # 295억
            "execution_rate": 98.33,
            "department": "복지정책과",
            "sub_department": "복지기획담당",
            "description": "저소득층, 장애인, 노인 등 취약계층 복지지원",
        },
        {
            "year": 2023,
            "category_code": "710",
            "item_name": "보건소 운영 및 방역사업",
            "budget_amount": 9500000000,  # 95억
            "executed_amount": 9200000000,  # 92억
            "execution_rate": 96.84,
            "department": "보건소",
            "sub_department": "보건행정과",
            "description": "시민 건강증진 및 감염병 예방사업",
        },
        {
            "year": 2023,
            "category_code": "820",
            "item_name": "수산업 육성 지원",
            "budget_amount": 7500000000,  # 75억
            "executed_amount": 7000000000,  # 70억
            "execution_rate": 93.33,
            "department": "해양수산과",
            "sub_department": "수산진흥담당",
            "description": "어업인 소득증대 및 수산업 현대화 지원",
        },
    ]
    
    async with AsyncSessionLocal() as session:
        for item_data in sample_items:
            budget_item = BudgetItem(**item_data)
            session.add(budget_item)
        
        await session.commit()
    
    print(f"✅ Initialized {len(sample_items)} sample budget items")


async def init_sample_population_data():
    """Initialize sample population data."""
    sample_population = [
        {
            "year": 2023,
            "region_code": "47130",
            "region_name": "포항시",
            "total_population": 500000,
            "male_population": 250000,
            "female_population": 250000,
            "household_count": 220000,
            "age_group_0_9": 35000,
            "age_group_10_19": 45000,
            "age_group_20_29": 55000,
            "age_group_30_39": 70000,
            "age_group_40_49": 80000,
            "age_group_50_59": 85000,
            "age_group_60_69": 75000,
            "age_group_70_plus": 55000,
        },
        {
            "year": 2023,
            "region_code": "47131",
            "region_name": "포항시 남구",
            "total_population": 220000,
            "male_population": 110000,
            "female_population": 110000,
            "household_count": 95000,
            "age_group_0_9": 15000,
            "age_group_10_19": 20000,
            "age_group_20_29": 25000,
            "age_group_30_39": 30000,
            "age_group_40_49": 35000,
            "age_group_50_59": 38000,
            "age_group_60_69": 32000,
            "age_group_70_plus": 25000,
        },
        {
            "year": 2023,
            "region_code": "47132",
            "region_name": "포항시 북구",
            "total_population": 280000,
            "male_population": 140000,
            "female_population": 140000,
            "household_count": 125000,
            "age_group_0_9": 20000,
            "age_group_10_19": 25000,
            "age_group_20_29": 30000,
            "age_group_30_39": 40000,
            "age_group_40_49": 45000,
            "age_group_50_59": 47000,
            "age_group_60_69": 43000,
            "age_group_70_plus": 30000,
        },
    ]
    
    async with AsyncSessionLocal() as session:
        for pop_data in sample_population:
            population = PopulationData(**pop_data)
            session.add(population)
        
        await session.commit()
    
    print(f"✅ Initialized {len(sample_population)} population data records")


async def crawl_real_data():
    """Crawl real data from SGIS API (optional)."""
    try:
        crawler = DataCrawler()
        data = await crawler.crawl_pohang_census_data(2023)
        
        # Transform and save population data
        if data.get("population"):
            transformed_pop = crawler.transform_population_data(data["population"], 2023)
            
            async with AsyncSessionLocal() as session:
                for pop_data in transformed_pop:
                    population = PopulationData(**pop_data)
                    session.add(population)
                
                await session.commit()
            
            print(f"✅ Crawled and saved {len(transformed_pop)} real population records")
        
    except Exception as e:
        print(f"⚠️  Failed to crawl real data: {e}")
        print("Using sample data instead")


async def initialize_database():
    """Initialize the entire database."""
    print("🚀 Starting database initialization...")
    
    # Create tables
    await create_tables()
    
    # Initialize data
    await init_budget_categories()
    await init_sample_budget_items()
    await init_sample_population_data()
    
    # Try to crawl real data (optional)
    # await crawl_real_data()
    
    print("🎉 Database initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(initialize_database())
