#!/usr/bin/env python3
"""
행정구역 정보 업데이트 스크립트
SGIS API에서 최신 행정구역 정보를 가져와서 캐시 업데이트 및 확인
"""
import sys
import asyncio
import logging
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.admin_areas import (
    get_admin_area_manager, 
    refresh_area_cache, 
    get_comprehensive_area_info
)
from src.agent.settings import get_enhanced_system_prompt

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_admin_areas():
    """행정구역 정보 업데이트"""
    logger.info("🔄 행정구역 정보 업데이트 시작")
    
    try:
        # 1. 캐시 강제 새로고침
        logger.info("1️⃣ SGIS API에서 행정구역 정보 새로고침...")
        areas = await refresh_area_cache()
        
        if not areas:
            logger.error("❌ 행정구역 정보 로드 실패")
            return False
        
        logger.info(f"✅ {len(areas)}개 행정구역 정보 로드 완료")
        
        # 2. 시도별 통계
        sido_count = len([code for code in areas.keys() if len(code) == 2])
        sigungu_count = len([code for code in areas.keys() if len(code) == 5])
        dong_count = len([code for code in areas.keys() if len(code) == 8])
        
        logger.info(f"📊 행정구역 분포:")
        logger.info(f"   - 시도: {sido_count}개")
        logger.info(f"   - 시군구: {sigungu_count}개")
        logger.info(f"   - 읍면동: {dong_count}개")
        
        # 3. 샘플 출력
        logger.info("📋 주요 시도 샘플:")
        sido_areas = {code: name for code, name in areas.items() if len(code) == 2}
        for code in sorted(list(sido_areas.keys())[:10]):
            logger.info(f"   - {code}: {sido_areas[code]}")
        
        # 4. 파일로 저장
        manager = get_admin_area_manager()
        backup_file = project_root / "admin_areas_backup.json"
        await manager.save_areas_to_file(areas, str(backup_file))
        logger.info(f"💾 백업 파일 저장: {backup_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 행정구역 업데이트 실패: {str(e)}")
        return False


async def test_prompt_generation():
    """프롬프트 생성 테스트"""
    logger.info("🧪 향상된 프롬프트 생성 테스트")
    
    try:
        # 1. 포괄적 행정구역 정보 생성 테스트
        logger.info("1️⃣ 행정구역 정보 문자열 생성...")
        area_info = await get_comprehensive_area_info()
        
        info_lines = area_info.count('\n')
        logger.info(f"✅ 행정구역 정보 생성 완료 ({info_lines}줄)")
        
        # 2. 향상된 시스템 프롬프트 생성 테스트
        logger.info("2️⃣ 향상된 시스템 프롬프트 생성...")
        enhanced_prompt = await get_enhanced_system_prompt()
        
        prompt_lines = enhanced_prompt.count('\n')
        prompt_chars = len(enhanced_prompt)
        logger.info(f"✅ 향상된 프롬프트 생성 완료 ({prompt_lines}줄, {prompt_chars:,}자)")
        
        # 3. 프롬프트 샘플 출력
        logger.info("📄 프롬프트 샘플 (처음 500자):")
        print("=" * 50)
        print(enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 프롬프트 생성 테스트 실패: {str(e)}")
        return False


async def validate_data():
    """데이터 유효성 검증"""
    logger.info("🔍 데이터 유효성 검증")
    
    try:
        manager = get_admin_area_manager()
        areas = await manager.get_all_administrative_areas()
        
        # 1. 기본 검증
        assert len(areas) > 0, "행정구역 데이터가 비어있음"
        logger.info(f"✅ 기본 검증 통과: {len(areas)}개 행정구역")
        
        # 2. 주요 시도 존재 확인
        major_sido = ['11', '26', '27', '28', '47']  # 서울, 부산, 대구, 인천, 경북
        missing_sido = []
        
        for sido_code in major_sido:
            if sido_code not in areas:
                missing_sido.append(sido_code)
        
        if missing_sido:
            logger.warning(f"⚠️ 누락된 주요 시도: {missing_sido}")
        else:
            logger.info("✅ 주요 시도 모두 존재")
        
        # 3. 코드 형식 검증
        invalid_codes = []
        for code in areas.keys():
            if not code.isdigit() or len(code) not in [2, 5, 8]:
                invalid_codes.append(code)
        
        if invalid_codes:
            logger.warning(f"⚠️ 잘못된 형식의 코드들: {invalid_codes[:10]}")
        else:
            logger.info("✅ 모든 코드 형식 유효")
        
        # 4. 포항 관련 코드 확인
        pohang_codes = {code: name for code, name in areas.items() if '포항' in name}
        logger.info(f"📍 포항 관련 행정구역 {len(pohang_codes)}개:")
        for code, name in sorted(pohang_codes.items()):
            logger.info(f"   - {code}: {name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터 검증 실패: {str(e)}")
        return False


async def main():
    """메인 함수"""
    logger.info("🚀 행정구역 정보 관리 도구 시작")
    
    tasks = [
        ("행정구역 정보 업데이트", update_admin_areas),
        ("프롬프트 생성 테스트", test_prompt_generation),
        ("데이터 유효성 검증", validate_data),
    ]
    
    success_count = 0
    
    for task_name, task_func in tasks:
        logger.info(f"\n📋 {task_name} 실행 중...")
        try:
            success = await task_func()
            if success:
                success_count += 1
                logger.info(f"✅ {task_name} 완료")
            else:
                logger.error(f"❌ {task_name} 실패")
        except Exception as e:
            logger.error(f"❌ {task_name} 중 오류: {str(e)}")
    
    logger.info(f"\n🏁 작업 완료: {success_count}/{len(tasks)} 성공")
    
    if success_count == len(tasks):
        logger.info("🎉 모든 작업이 성공적으로 완료되었습니다!")
        return 0
    else:
        logger.error("⚠️ 일부 작업이 실패했습니다.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
