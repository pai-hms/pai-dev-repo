"""Data API routes for budget and population data."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from webapp.models import BudgetItemResponse, PopulationDataResponse, QueryHistoryResponse
from webapp.dependencies import get_budget_repository, get_population_repository, get_query_repository
from src.database.repository import BudgetRepository, PopulationRepository, QueryRepository

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/budget/categories")
async def get_budget_categories(
    budget_repo: BudgetRepository = Depends(get_budget_repository),
):
    """Get all budget categories."""
    try:
        categories = await budget_repo.get_budget_categories()
        return {
            "success": True,
            "data": [
                {
                    "id": cat.id,
                    "code": cat.code,
                    "name": cat.name,
                    "parent_code": cat.parent_code,
                    "level": cat.level,
                    "description": cat.description,
                }
                for cat in categories
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget/items", response_model=List[BudgetItemResponse])
async def get_budget_items(
    year: int = Query(2023, description="Budget year"),
    category_code: Optional[str] = Query(None, description="Filter by category code"),
    limit: int = Query(100, le=1000, description="Maximum number of items to return"),
    budget_repo: BudgetRepository = Depends(get_budget_repository),
):
    """Get budget items with optional filtering."""
    try:
        if category_code:
            items = await budget_repo.get_budget_items_by_category(category_code)
        else:
            items = await budget_repo.get_budget_items_by_year(year)
        
        # Limit results
        items = items[:limit]
        
        return [
            BudgetItemResponse(
                id=item.id,
                year=item.year,
                category_code=item.category_code,
                item_name=item.item_name,
                budget_amount=float(item.budget_amount),
                executed_amount=float(item.executed_amount) if item.executed_amount else None,
                execution_rate=float(item.execution_rate) if item.execution_rate else None,
                department=item.department,
                sub_department=item.sub_department,
            )
            for item in items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/population", response_model=List[PopulationDataResponse])
async def get_population_data(
    year: int = Query(2023, description="Census year"),
    region_code: Optional[str] = Query(None, description="Filter by region code"),
    limit: int = Query(100, le=1000, description="Maximum number of items to return"),
    population_repo: PopulationRepository = Depends(get_population_repository),
):
    """Get population data with optional filtering."""
    try:
        if region_code:
            data = await population_repo.get_population_by_region(region_code)
        else:
            data = await population_repo.get_population_by_year(year)
        
        # Limit results
        data = data[:limit]
        
        return [
            PopulationDataResponse(
                id=item.id,
                year=item.year,
                region_code=item.region_code,
                region_name=item.region_name,
                total_population=item.total_population,
                male_population=item.male_population,
                female_population=item.female_population,
                household_count=item.household_count,
            )
            for item in data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/history", response_model=List[QueryHistoryResponse])
async def get_query_history(
    limit: int = Query(20, le=100, description="Maximum number of queries to return"),
    query_repo: QueryRepository = Depends(get_query_repository),
):
    """Get recent query history."""
    try:
        queries = await query_repo.get_recent_queries(limit)
        
        return [
            QueryHistoryResponse(
                id=query.id,
                user_question=query.user_question,
                generated_sql=query.generated_sql,
                execution_result=query.execution_result,
                success=bool(query.success),
                execution_time_ms=query.execution_time_ms,
                created_at=query.created_at,
            )
            for query in queries
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
