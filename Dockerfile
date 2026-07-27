FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

RUN python -m pytest tests/ -x -q

ENTRYPOINT ["python", "-m", "src.governance.runner"]

FROM base AS with-rl
COPY requirements-rl.txt .
RUN pip install --no-cache-dir -r requirements-rl.txt
RUN python -m pytest tests/ -x -q
