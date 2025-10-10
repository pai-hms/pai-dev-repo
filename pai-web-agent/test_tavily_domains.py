#!/usr/bin/env python3
"""
Tavily API 도메인 필터링 테스트 스크립트

다양한 도메인 형식으로 Tavily API를 직접 호출하여 
어떤 형식이 유효한지 테스트합니다.
"""

import os
import requests
import json
from typing import List, Optional
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

def test_tavily_domains(query: str, include_domains: List[str], api_key: str):
    """
    Tavily API로 직접 도메인 필터링 테스트
    
    Args:
        query: 검색 쿼리
        include_domains: 포함할 도메인 리스트
        api_key: Tavily API 키
        
    Returns:
        API 응답 결과
    """
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 3,
        "include_domains": include_domains
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"🔍 테스트: {include_domains}")
        print(f"📡 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ 성공! 결과 {len(results)}개")
            
            # 결과 도메인 확인
            if results:
                domains_found = set()
                for result in results:
                    url = result.get("url", "")
                    if url:
                        domain = url.split("//")[-1].split("/")[0]
                        domains_found.add(domain)
                print(f"📋 발견된 도메인: {', '.join(sorted(domains_found))}")
            
            return {"success": True, "results": results, "error": None}
            
        else:
            error_text = response.text
            print(f"❌ 실패: {error_text}")
            return {"success": False, "results": [], "error": error_text}
            
    except Exception as e:
        print(f"💥 예외 발생: {str(e)}")
        return {"success": False, "results": [], "error": str(e)}

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🧪 Tavily API 도메인 필터링 테스트")
    print("=" * 60)
    
    # API 키 확인
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("❌ TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")
        print("💡 사용법: TAVILY_API_KEY=your_key python test_tavily_domains.py")
        return
    
    # 테스트 쿼리
    test_query = "한국 정부 정책"
    
    # 다양한 도메인 형식 테스트
    test_cases = [
        # 와일드카드 형식
        (["*.go.kr"], "와일드카드 - 정부기관"),
        (["*.or.kr"], "와일드카드 - 공공기관"),
        (["*.go.kr", "*.or.kr"], "와일드카드 - 정부+공공기관"),
        
        # 특정 도메인 형식
        (["moef.go.kr"], "특정 도메인 - 기획재정부"),
        (["kostat.go.kr"], "특정 도메인 - 통계청"),
        (["kosis.kr"], "특정 도메인 - 통계정보시스템"),
        
        # 잘못된 형식들
        (["go.kr"], "잘못된 형식 - go.kr (와일드카드 없음)"),
        (["or.kr"], "잘못된 형식 - or.kr (와일드카드 없음)"),
        ([".go.kr"], "잘못된 형식 - .go.kr (점으로 시작)"),
        ([".or.kr"], "잘못된 형식 - .or.kr (점으로 시작)"),
        
        # 일반 도메인 (비교용)
        (["*.com"], "일반 도메인 - *.com"),
        (["naver.com"], "특정 도메인 - naver.com"),
    ]
    
    print(f"🔍 검색 쿼리: '{test_query}'")
    print()
    
    # 각 테스트 케이스 실행
    success_count = 0
    total_count = len(test_cases)
    
    for i, (domains, description) in enumerate(test_cases, 1):
        print(f"[{i:2d}/{total_count}] {description}")
        result = test_tavily_domains(test_query, domains, api_key)
        
        if result["success"]:
            success_count += 1
        
        print("-" * 40)
        print()
    
    # 결과 요약
    print("=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {success_count}/{total_count}")
    print(f"❌ 실패: {total_count - success_count}/{total_count}")
    
    if success_count > 0:
        print("\n💡 권장사항:")
        print("- 성공한 도메인 형식을 사용하세요")
        print("- 와일드카드(*.domain.com) 형식이 일반적으로 권장됩니다")
    else:
        print("\n⚠️  모든 테스트가 실패했습니다.")
        print("- API 키를 확인하세요")
        print("- 네트워크 연결을 확인하세요")

if __name__ == "__main__":
    main()
