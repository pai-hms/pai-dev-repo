#!/usr/bin/env python3
"""
기본 기능 테스트 스크립트
"""
import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        from src.database.connection import get_database_manager
        
        print("🔍 데이터베이스 연결 테스트...")
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            from src.database.repository import DatabaseService
            db_service = DatabaseService(session)
            
            # 간단한 쿼리 실행
            result = await db_service.execute_raw_query("SELECT 1 as test")
            
            if result and result[0]["test"] == 1:
                print("✅ 데이터베이스 연결 성공")
                return True
            else:
                print("❌ 데이터베이스 쿼리 실패")
                return False
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")
        return False


async def test_sgis_client():
    """SGIS 클라이언트 테스트"""
    try:
        from src.crawler.sgis_client import SGISClient
        
        print("🔍 SGIS API 연결 테스트...")
        client = SGISClient()
        
        # 토큰 획득 테스트
        token = await client._get_access_token()
        
        if token:
            print("✅ SGIS API 연결 성공")
            return True
        else:
            print("❌ SGIS API 토큰 획득 실패")
            return False
            
    except Exception as e:
        print(f"❌ SGIS API 연결 실패: {str(e)}")
        return False


async def test_sql_tools():
    """SQL 도구 테스트"""
    try:
        from src.agent.tools import SQLQueryValidator
        
        print("🔍 SQL 도구 테스트...")
        
        # 유효한 쿼리 테스트
        valid_query = "SELECT adm_cd, adm_nm FROM population_stats WHERE year = 2023 LIMIT 10"
        is_valid, error = SQLQueryValidator.validate_query(valid_query)
        
        if is_valid:
            print("✅ SQL 검증 도구 정상")
        else:
            print(f"❌ SQL 검증 도구 오류: {error}")
            return False
            
        # 위험한 쿼리 테스트
        dangerous_query = "DROP TABLE population_stats"
        is_valid, error = SQLQueryValidator.validate_query(dangerous_query)
        
        if not is_valid:
            print("✅ SQL 보안 검증 정상")
            return True
        else:
            print("❌ SQL 보안 검증 실패")
            return False
            
    except Exception as e:
        print(f"❌ SQL 도구 테스트 실패: {str(e)}")
        return False


async def test_agent_graph():
    """에이전트 그래프 테스트"""
    try:
        from src.agent.graph import get_sql_agent_graph
        
        print("🔍 에이전트 그래프 테스트...")
        
        # 체크포인터 없이 간단한 그래프 생성
        agent_graph = get_sql_agent_graph(enable_checkpointer=False)
        graph = await agent_graph.get_compiled_graph()
        
        if graph:
            print("✅ 에이전트 그래프 생성 성공")
            return True
        else:
            print("❌ 에이전트 그래프 생성 실패")
            return False
            
    except Exception as e:
        print(f"❌ 에이전트 그래프 테스트 실패: {str(e)}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 PAI SQL Agent 기본 기능 테스트 시작\n")
    
    tests = [
        ("데이터베이스 연결", test_database_connection),
        ("SGIS API 연결", test_sgis_client),
        ("SQL 도구", test_sql_tools),
        ("에이전트 그래프", test_agent_graph),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {str(e)}\n")
            results.append((test_name, False))
    
    # 결과 요약
    print("=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트가 통과했습니다!")
        return 0
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
