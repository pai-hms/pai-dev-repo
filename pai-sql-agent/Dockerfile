FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry

# Poetry 설정
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# pyproject.toml 복사
COPY pyproject.toml ./

# 의존성 설치
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# 소스 코드 복사
COPY . .

EXPOSE 8000

# Poetry 가상환경을 직접 활성화하고 실행
CMD ["sh", "-c", ". /app/.venv/bin/activate && uvicorn webapp.main:app --host 0.0.0.0 --port 8000"]