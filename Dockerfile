FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra dashboard --extra rl

COPY src/ src/
COPY tests/ tests/
COPY examples/ examples/
RUN uv sync --frozen --no-dev --extra dashboard && .venv/bin/python -m pytest tests/ -x -q

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "nomos.runner"]

FROM base AS with-rl

RUN uv sync --frozen --no-dev --extra rl --extra dashboard && .venv/bin/python -m pytest tests/ -x -q