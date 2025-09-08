"""Database models for Pohang City budget data."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from .connection import Base


class BudgetCategory(Base):
    """Budget category model."""
    
    __tablename__ = "budget_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    parent_code = Column(String(20), ForeignKey("budget_categories.code"), nullable=True)
    level = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship
    parent = relationship("BudgetCategory", remote_side=[code], backref="children")
    
    # Relationship to budget items
    budget_items = relationship("BudgetItem", back_populates="category")


class BudgetItem(Base):
    """Budget item model for 2023 Pohang City budget data."""
    
    __tablename__ = "budget_items"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    category_code = Column(String(20), ForeignKey("budget_categories.code"), nullable=False)
    item_name = Column(String(500), nullable=False)
    budget_amount = Column(Numeric(15, 2), nullable=False)
    executed_amount = Column(Numeric(15, 2), nullable=True)
    execution_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    department = Column(String(100), nullable=True)
    sub_department = Column(String(100), nullable=True)
    project_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to category
    category = relationship("BudgetCategory", back_populates="budget_items")


class PopulationData(Base):
    """Population census data model."""
    
    __tablename__ = "population_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_population = Column(Integer, nullable=False)
    male_population = Column(Integer, nullable=True)
    female_population = Column(Integer, nullable=True)
    household_count = Column(Integer, nullable=True)
    age_group_0_9 = Column(Integer, nullable=True)
    age_group_10_19 = Column(Integer, nullable=True)
    age_group_20_29 = Column(Integer, nullable=True)
    age_group_30_39 = Column(Integer, nullable=True)
    age_group_40_49 = Column(Integer, nullable=True)
    age_group_50_59 = Column(Integer, nullable=True)
    age_group_60_69 = Column(Integer, nullable=True)
    age_group_70_plus = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HouseholdData(Base):
    """Household census data model."""
    
    __tablename__ = "household_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_households = Column(Integer, nullable=False)
    ordinary_households = Column(Integer, nullable=True)
    collective_households = Column(Integer, nullable=True)
    single_person_households = Column(Integer, nullable=True)
    multi_person_households = Column(Integer, nullable=True)
    average_household_size = Column(Numeric(4, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HousingData(Base):
    """Housing census data model."""
    
    __tablename__ = "housing_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_houses = Column(Integer, nullable=False)
    detached_houses = Column(Integer, nullable=True)
    apartment_houses = Column(Integer, nullable=True)
    row_houses = Column(Integer, nullable=True)
    multi_unit_houses = Column(Integer, nullable=True)
    other_houses = Column(Integer, nullable=True)
    owned_houses = Column(Integer, nullable=True)
    rented_houses = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyData(Base):
    """Company/Business census data model."""
    
    __tablename__ = "company_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_companies = Column(Integer, nullable=False)
    total_employees = Column(Integer, nullable=True)
    manufacturing_companies = Column(Integer, nullable=True)
    service_companies = Column(Integer, nullable=True)
    retail_companies = Column(Integer, nullable=True)
    construction_companies = Column(Integer, nullable=True)
    other_companies = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IndustryData(Base):
    """Industry classification data model."""
    
    __tablename__ = "industry_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    industry_code = Column(String(10), nullable=False, index=True)
    industry_name = Column(String(200), nullable=False)
    company_count = Column(Integer, nullable=False)
    employee_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgriculturalHouseholdData(Base):
    """Agricultural household data model."""
    
    __tablename__ = "agricultural_household_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_farm_households = Column(Integer, nullable=False)
    full_time_farmers = Column(Integer, nullable=True)
    part_time_farmers = Column(Integer, nullable=True)
    farm_population = Column(Integer, nullable=True)
    cultivated_area = Column(Numeric(12, 2), nullable=True)  # in hectares
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForestryHouseholdData(Base):
    """Forestry household data model."""
    
    __tablename__ = "forestry_household_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_forestry_households = Column(Integer, nullable=False)
    forestry_population = Column(Integer, nullable=True)
    forest_area = Column(Numeric(12, 2), nullable=True)  # in hectares
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FisheryHouseholdData(Base):
    """Fishery household data model."""
    
    __tablename__ = "fishery_household_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    total_fishery_households = Column(Integer, nullable=False)
    fishery_population = Column(Integer, nullable=True)
    fishing_boats = Column(Integer, nullable=True)
    aquaculture_farms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HouseholdMemberData(Base):
    """Household member demographic data model."""
    
    __tablename__ = "household_member_data"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    region_code = Column(String(20), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    household_type = Column(String(50), nullable=False)  # e.g., 'single', 'couple', 'family'
    member_count = Column(Integer, nullable=False)
    male_members = Column(Integer, nullable=True)
    female_members = Column(Integer, nullable=True)
    children_count = Column(Integer, nullable=True)
    elderly_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QueryHistory(Base):
    """Query execution history for agent learning."""
    
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_question = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    execution_result = Column(Text, nullable=True)
    success = Column(Integer, nullable=False, default=1)  # 1 for success, 0 for failure
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentCheckpoint(Base):
    """Agent state checkpoints for persistence."""
    
    __tablename__ = "agent_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    checkpoint_id = Column(String(100), nullable=False)
    state_data = Column(Text, nullable=False)  # JSON serialized state
    metadata = Column(Text, nullable=True)  # JSON serialized metadata
    created_at = Column(DateTime, default=datetime.utcnow)
