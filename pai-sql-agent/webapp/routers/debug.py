"""
디버그 및 데이터베이스 상태 확인 API 라우터
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database_manager
from src.database.repository import DatabaseService
from src.rag.service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["데이터베이스 디버그"])


@router.get("/database-info")
async def get_database_info() -> Dict[str, Any]:
    """
    데이터베이스 상태 정보 조회
    - 테이블 목록 및 레코드 수
    - 최신 데이터 샘플
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 테이블 목록 조회
            all_tables = await db_service.get_all_tables()
            
            tables_info = []
            sample_data = []
            
            for table_name in all_tables:
                try:
                    # 테이블별 레코드 수 조회
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    count_result = await db_service.execute_raw_query(count_query)
                    row_count = count_result[0]['count'] if count_result else 0
                    
                    tables_info.append({
                        "table_name": table_name,
                        "row_count": row_count
                    })
                    
                    # 샘플 데이터 조회 (인구 통계만)
                    if table_name == "population_stats" and row_count > 0:
                        sample_query = f"SELECT * FROM {table_name} ORDER BY year DESC, tot_ppltn DESC LIMIT 3"
                        sample_result = await db_service.execute_raw_query(sample_query)
                        
                        if sample_result:
                            for row in sample_result:
                                sample_data.append({
                                    "table": table_name,
                                    "adm_cd": row.get("adm_cd"),
                                    "adm_nm": row.get("adm_nm"), 
                                    "year": row.get("year"),
                                    "tot_ppltn": row.get("tot_ppltn"),
                                    "avg_age": row.get("avg_age")
                                })
                    
                except Exception as table_error:
                    logger.warning(f"테이블 {table_name} 정보 조회 실패: {table_error}")
                    tables_info.append({
                        "table_name": table_name,
                        "row_count": 0,
                        "error": str(table_error)
                    })
            
            # 샘플 데이터 포맷팅
            sample_text = ""
            if sample_data:
                sample_text = "최신 인구 통계 샘플:\n"
                for sample in sample_data[:3]:
                    sample_text += f"• {sample['adm_nm']} ({sample['year']}): {sample['tot_ppltn']:,}명"
                    if sample.get('avg_age'):
                        sample_text += f", 평균연령 {sample['avg_age']}세"
                    sample_text += "\n"
            
            return {
                "success": True,
                "total_tables": len(all_tables),
                "tables": tables_info,
                "sample_data": sample_text,
                "database_status": "healthy"
            }
            
    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "database_status": "error"
        }


@router.get("/vector-info")
async def get_vector_db_info() -> Dict[str, Any]:
    """
    벡터 데이터베이스 상태 정보 조회
    - 임베딩 총 개수
    - 테이블별 임베딩 현황
    - 최근 임베딩 예시
    """
    try:
        rag_service = get_rag_service()
        
        # 임베딩 통계 조회
        stats = await rag_service.get_embedding_statistics()
        
        # 추가 세부 정보 조회
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            # 벡터 DB 테이블 존재 확인
            vector_tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'document_embeddings'
            """
            vector_tables = await db_service.execute_raw_query(vector_tables_query)
            
            recent_embeddings = []
            if vector_tables:
                # 최근 임베딩 조회
                recent_query = """
                SELECT content, source_table, source_id, created_at
                FROM document_embeddings
                ORDER BY created_at DESC
                LIMIT 5
                """
                recent_result = await db_service.execute_raw_query(recent_query)
                
                if recent_result:
                    recent_embeddings = [
                        {
                            "content": row["content"][:100] + "..." if len(row["content"]) > 100 else row["content"],
                            "source_table": row["source_table"],
                            "source_id": row["source_id"],
                            "created_at": str(row["created_at"])
                        }
                        for row in recent_result
                    ]
        
        return {
            "success": True,
            "total_embeddings": stats.get("total_embedded", 0),
            "tables": stats.get("tables", []),
            "overall_completion": stats.get("overall_completion", 0),
            "recent_embeddings": recent_embeddings,
            "vector_db_status": "healthy" if stats.get("total_embedded", 0) > 0 else "empty"
        }
        
    except Exception as e:
        logger.error(f"벡터 DB 정보 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "vector_db_status": "error"
        }


@router.post("/create-embeddings")
async def create_embeddings() -> Dict[str, Any]:
    """
    임베딩 생성/업데이트 트리거
    2023년 데이터 기준으로 임베딩 생성
    """
    try:
        rag_service = get_rag_service()
        
        # 2023년 인구 통계 임베딩 생성
        result = await rag_service.create_embeddings_for_population_stats(2023)
        
        if result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "임베딩 생성 완료"),
                "created_count": result.get("created_count", 0),
                "error_count": result.get("error_count", 0)
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "임베딩 생성 실패"),
                "created_count": result.get("created_count", 0),
                "error_count": result.get("error_count", 0)
            }
            
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "created_count": 0,
            "error_count": 1
        }


@router.get("/analyze-query-issue")
async def analyze_query_issue(question: str = "서울 인구") -> Dict[str, Any]:
    """
    질문 처리 과정 분석 (디버깅용)
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            db_service = DatabaseService(session)
            
            analysis = {
                "question": question,
                "steps": []
            }
            
            # 1. 데이터 존재 확인
            analysis["steps"].append("1. 데이터 존재 확인")
            population_query = """
            SELECT COUNT(*) as count 
            FROM population_stats 
            WHERE adm_nm LIKE '%서울%' AND year = 2023
            """
            pop_result = await db_service.execute_raw_query(population_query)
            seoul_data_count = pop_result[0]["count"] if pop_result else 0
            analysis["seoul_data_available"] = seoul_data_count > 0
            analysis["seoul_data_count"] = seoul_data_count
            
            # 2. 벡터 검색 확인
            analysis["steps"].append("2. 벡터 검색 확인")
            try:
                rag_service = get_rag_service()
                search_results = await rag_service.search_similar_documents(
                    query=question,
                    top_k=3,
                    similarity_threshold=0.1
                )
                analysis["vector_search_results"] = len(search_results)
                if search_results:
                    analysis["vector_search_samples"] = [
                        {
                            "content": r.content[:100] + "...",
                            "similarity": r.similarity,
                            "source": r.source_table
                        }
                        for r in search_results[:2]
                    ]
            except Exception as vector_error:
                analysis["vector_search_error"] = str(vector_error)
            
            # 3. 직접 SQL 테스트
            analysis["steps"].append("3. 직접 SQL 테스트")
            direct_query = """
            SELECT adm_nm, tot_ppltn, avg_age
            FROM population_stats 
            WHERE adm_nm LIKE '%서울%' AND year = 2023
            ORDER BY tot_ppltn DESC
            LIMIT 3
            """
            direct_result = await db_service.execute_raw_query(direct_query)
            analysis["direct_sql_results"] = len(direct_result) if direct_result else 0
            if direct_result:
                analysis["direct_sql_samples"] = [
                    {
                        "region": row["adm_nm"],
                        "population": row["tot_ppltn"],
                        "avg_age": row["avg_age"]
                    }
                    for row in direct_result
                ]
            
            return {
                "success": True,
                "analysis": analysis
            }
            
    except Exception as e:
        logger.error(f"쿼리 이슈 분석 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }
