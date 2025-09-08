FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

# Poetry
RUN pip install --no-cache-dir poetry

# Poetry 설정 (프로젝트 내부 .venv 유지)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR=/root/.cache/pypoetry

# 의존성만 설치
COPY pyproject.toml poetry.lock* ./
# alembic 이 dev 그룹에 있다면 --with dev(또는 --with migrations) 추가
RUN poetry install --no-root --only main --with migrations

# 소스 복사
COPY . .

EXPOSE 8000

# venv 를 확실히 사용해서 실행
CMD ["/bin/sh", "-lc", ". .venv/bin/activate && alembic upgrade head && uvicorn webapp.main:app --host 0.0.0.0 --port 8000"]
