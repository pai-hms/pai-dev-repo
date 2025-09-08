#!/bin/bash

# PAI SQL Agent Docker 실행 스크립트

echo "PAI SQL Agent 시작 중..."

# 환경변수 파일 확인
if [ ! -f .env ]; then
    echo ".env 파일이 없습니다."
    echo "다음 명령어로 생성하세요:"
    echo "cp env.example .env"
    echo "# .env 파일에서 OPENAI_API_KEY 설정 필수!"
    exit 1
fi

# OpenAI API 키 확인
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo ".env 파일에서 OPENAI_API_KEY를 설정해주세요."
fi

# Docker 실행
echo "Docker Compose 시작 중..."
docker-compose up --build

echo ""
echo "PAI SQL Agent 실행 완료!"
echo " 웹 서비스: http://localhost:8000"
echo " API 문서: http://localhost:8000/docs"
