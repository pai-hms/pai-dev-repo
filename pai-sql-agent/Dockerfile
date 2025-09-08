# PAI SQL Agent Dockerfile - UV 올바른 사용
FROM python:3.11-slim


# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# UV 설치
RUN pip install --no-cache-dir uv

# 프로젝트 파일 복사
COPY . .

# UV로 의존성 설치 (pyproject.toml 기반)
RUN uv sync --no-dev --frozen

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 실행 명령어
CMD ["uv", "run", "uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]