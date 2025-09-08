#!/bin/bash

echo "=== PAI SQL Agent 시작 ==="

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. env.example을 복사하여 .env 파일을 생성하고 API 키를 설정하세요."
    cp env.example .env
    echo "📝 .env 파일이 생성되었습니다. API 키를 설정한 후 다시 실행하세요."
    exit 1
fi

# OpenAI API 키 확인
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  OpenAI API 키가 설정되지 않았습니다."
    echo "📝 .env 파일에서 OPENAI_API_KEY를 설정하세요."
    exit 1
fi

# SGIS API 키 확인  
if ! grep -q "SGIS_ACCESS_KEY=" .env || ! grep -q "SGIS_SECRET_KEY=" .env; then
    echo "⚠️  SGIS API 키가 설정되지 않았습니다."
    echo "📝 .env 파일에서 SGIS_ACCESS_KEY와 SGIS_SECRET_KEY를 설정하세요."
    echo "🔗 SGIS API 키 발급: https://sgis.kostat.go.kr/developer/"
    exit 1
fi

echo "✅ 환경 변수 확인 완료"

# Docker Compose 실행
echo "🐳 Docker 컨테이너 시작 중..."
docker-compose up -d postgres

# PostgreSQL 준비 대기
echo "⏳ PostgreSQL 시작 대기 중..."
sleep 10

# 데이터베이스 초기화 확인
echo "🗄️  데이터베이스 상태 확인 중..."
docker-compose exec postgres pg_isready -U pai_user -d pai_sql_agent

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL 준비 완료"
else
    echo "❌ PostgreSQL 연결 실패"
    exit 1
fi

# 애플리케이션 시작
echo "🚀 애플리케이션 시작 중..."
docker-compose up -d app

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 15

# API 서버 상태 확인
echo "🔍 API 서버 상태 확인 중..."
if curl -s http://localhost:8000/api/data/health > /dev/null; then
    echo "✅ API 서버 정상 작동"
else
    echo "⚠️  API 서버 응답 없음. 로그를 확인하세요: docker-compose logs app"
fi

# Streamlit 앱 상태 확인
echo "🔍 Streamlit 앱 상태 확인 중..."
if curl -s http://localhost:8501 > /dev/null; then
    echo "✅ Streamlit 앱 정상 작동"
else
    echo "⚠️  Streamlit 앱 응답 없음. 로그를 확인하세요: docker-compose logs app"
fi

echo ""
echo "🎉 PAI SQL Agent가 시작되었습니다!"
echo ""
echo "📊 Streamlit 웹앱: http://localhost:8501"
echo "🔗 API 문서: http://localhost:8000/docs"
echo "💾 PostgreSQL: localhost:5432"
echo ""
echo "📋 유용한 명령어:"
echo "  로그 확인: docker-compose logs -f"
echo "  서비스 중지: docker-compose down"
echo "  데이터 초기화: docker-compose exec app python -m src.database.init_data"
echo ""
