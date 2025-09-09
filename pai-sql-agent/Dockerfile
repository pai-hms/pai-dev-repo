# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 및 PATH 설정을 한 번에
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# 전체 소스 코드 복사 (의존성 설치 전에)
COPY . .

# uv를 사용한 의존성 설치 (프로덕션 의존성만)
RUN uv pip install --system --no-cache .

# 포트 노출
EXPOSE 8000

# FastAPI 실행
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]