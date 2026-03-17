FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy dependency files
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root --only main 2>/dev/null || \
    pip install httpx[http2] aiohttp websockets py-clob-client web3 openai instructor pandas numpy redis sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings loguru orjson click python-telegram-bot[job-queue] fastapi uvicorn

# Copy app code
COPY . .

# Create data/logs dirs
RUN mkdir -p data logs

EXPOSE 8501 8601

CMD ["python", "main.py", "--mode", "paper"]
