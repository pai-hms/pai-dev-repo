#!/usr/bin/env python3
"""
간단한 메모리 테스트 스크립트 (도커용)
AsyncPostgresSaver 기반 메모리 기능이 제대로 작동하는지 확인
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_memory_quick():
    """빠른 메모리 기능 테스트"""
    print("\n🧠 AsyncPostgresSaver 메모리 기능 테스트")
    print("=" * 60)
    
    try:
        from src.agent.graph import get_sql_agent_service
        
        # 체크포인터 활성화된 서비스 생성
        service = get_sql_agent_service(enable_checkpointer=True)
        session_id = f"test_memory_{int(datetime.now().timestamp())}"
        
        print(f"🔑 테스트 세션 ID: {session_id}")
        
        # 1단계: 첫 번째 질문 (자기소개)
        print("\n1️⃣ 첫 번째 질문: 자기소개")
        question1 = "안녕하세요! 저는 홍민식입니다."
        
        result1 = await service.invoke_query(question1, session_id=session_id)
        
        if result1.get('error_message'):
            print(f"❌ 첫 번째 질문 실패: {result1['error_message']}")
            return False
        
        print("✅ 첫 번째 질문 완료")
        messages1 = result1.get('messages', [])
        print(f"   📝 메시지 수: {len(messages1)}")
        
        if messages1:
            last_msg = messages1[-1]
            if hasattr(last_msg, 'content'):
                print(f"   💬 응답 미리보기: {last_msg.content[:100]}...")
        
        # 2단계: 두 번째 질문 (메모리 테스트)
        print("\n2️⃣ 두 번째 질문: 메모리 테스트")
        question2 = "제 이름이 뭐라고 했죠?"
        
        result2 = await service.invoke_query(question2, session_id=session_id)
        
        if result2.get('error_message'):
            print(f"❌ 두 번째 질문 실패: {result2['error_message']}")
            return False
        
        print("✅ 두 번째 질문 완료")
        messages2 = result2.get('messages', [])
        print(f"   📝 메시지 수: {len(messages2)}")
        
        if messages2:
            last_msg = messages2[-1]
            if hasattr(last_msg, 'content'):
                answer2 = last_msg.content
                print(f"   💬 응답: {answer2[:200]}...")
                
                # 메모리 작동 확인
                memory_working = any(name in answer2 for name in ["홍민식", "민식", "홍"])
                
                if memory_working:
                    print("🎉 메모리 기능이 정상 작동합니다!")
                    return True
                else:
                    print("⚠️ 메모리 기능이 제대로 작동하지 않을 수 있습니다.")
                    print(f"   검색 대상: ['홍민식', '민식', '홍']")
                    print(f"   실제 응답: {answer2}")
                    return False
        
        return False
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        print(f"❌ 테스트 오류 상세: {str(e)}")
        return False


async def main():
    """메인 함수"""
    print("🔍 간단한 메모리 기능 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 환경 변수 확인
        db_url = os.environ.get('DATABASE_URL', 'Not set')
        openai_key = os.environ.get('OPENAI_API_KEY', 'Not set')
        
        print(f"\n🌍 환경 정보:")
        print(f"   🐍 Python: {sys.version.split()[0]}")
        print(f"   📊 DATABASE_URL: {db_url[:50]}...")
        print(f"   🤖 OPENAI_API_KEY: {'설정됨' if openai_key != 'Not set' else '설정 안됨'}")
        
        if db_url == 'Not set':
            print("⚠️ DATABASE_URL이 설정되지 않았습니다.")
            print("   도커 환경에서는 자동으로 설정됩니다.")
        
        if openai_key == 'Not set':
            print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
            print("   .env 파일에서 설정하거나 환경 변수로 제공해주세요.")
        
        # 테스트 실행
        success = await test_memory_quick()
        
        print(f"\n📋 테스트 결과:")
        if success:
            print("🎉 메모리 기능 테스트 성공!")
            print("   - 대화 기록이 PostgreSQL에 저장됨")
            print("   - 연속 대화가 정상 작동함")
            print("   - 'What was my name?' 같은 질문 처리 가능")
        else:
            print("❌ 메모리 기능 테스트 실패")
            print("   - 환경 설정을 확인해주세요")
            print("   - 도커 로그를 확인해보세요")
        
        print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n💥 테스트 실행 중 예외 발생: {e}")
        print(f"상세 오류: {str(e)}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 테스트 실행 중 예외 발생: {e}")
        sys.exit(1)
