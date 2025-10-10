#!/usr/bin/env python3
"""
Streamlit 앱 실행 스크립트
"""

import subprocess
import sys
import os

def run_main_app():
    """메인 Streamlit 앱 실행"""
    print("🚀 PAI Web Agent를 실행합니다...")
    print("📱 브라우저에서 http://localhost:8501 를 열어주세요")
    print("🛑 종료하려면 Ctrl+C를 누르세요\n")
    
    try:
        subprocess.run(["uv", "run", "streamlit", "run", "app.py", "--server.port", "8501"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Streamlit 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def run_simple_app():
    """간단한 Streamlit 앱 실행"""
    print("🚀 간단한 PAI Web Agent를 실행합니다...")
    print("📱 브라우저에서 http://localhost:8502 를 열어주세요")
    print("🛑 종료하려면 Ctrl+C를 누르세요\n")
    
    try:
        subprocess.run(["uv", "run", "streamlit", "run", "app_simple.py", "--server.port", "8502"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Streamlit 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "simple":
            run_simple_app()
        else:
            run_main_app()
    else:
        run_main_app()

if __name__ == "__main__":
    main()
