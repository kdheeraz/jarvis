FROM python:3.11.9-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libsndfile1 \
    ffmpeg \
    sox \
    libsox-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Dev target (used by docker-compose.dev.yaml)
FROM base AS dev
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchaudio
RUN pip install --no-cache-dir ".[dev,voice,rag]"
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# Production target
FROM base AS production
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchaudio
RUN pip install --no-cache-dir ".[voice,rag]"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
