FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Try Poetry first, fallback to pip with complete dependency list
COPY pyproject.toml ./

# Try using Poetry with lock file if available
RUN if [ -f poetry.lock ]; then \
    pip install --no-cache-dir poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root; \
    else \
    echo "No poetry.lock found, using pip"; \
    fi

# If Poetry install failed, fallback to pip with complete dependency list
RUN pip install --no-cache-dir --break-system-packages \
    httpx[http2] \
    aiohttp \
    websockets \
    "py-clob-client>=0.18.0" \
    "web3>=6.0.0" \
    "openai>=1.30.0" \
    "instructor>=1.2.0" \
    "pandas>=2.2.0" \
    "numpy>=1.26.0" \
    "redis>=5.0.3" \
    "sqlalchemy>=2.0.29" \
    "aiosqlite>=0.20.0" \
    "alembic>=1.13.1" \
    "fastapi>=0.110.0" \
    "uvicorn>=0.29.0" \
    "streamlit>=1.33.0" \
    "python-telegram-bot>=21.0" \
    "pydantic>=2.6.0" \
    "pydantic-settings>=2.2.0" \
    "python-dotenv>=1.0.0" \
    "loguru>=0.7.2" \
    "orjson>=3.9.15" \
    "click>=8.1.7" \
    "apscheduler>=3.10.4" \
    "pytest>=8.1.1" \
    "pytest-asyncio>=0.23.6" \
    2>/dev/null || true

# Copy app code
COPY . .

# Create data/logs dirs
RUN mkdir -p data logs db

EXPOSE 8501 8601

CMD ["python", "main.py", "--mode", "paper"]
