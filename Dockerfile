# ─── Stage 1: Builder ───
FROM python:3.10-slim AS builder

# System deps for sentence-transformers (needs gcc for some C-extension wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ───
FROM python:3.10-slim

# Minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY chasm/ ./chasm/
COPY main.py .
COPY requirements.txt .

# Create persistent data directories
RUN mkdir -p chasm/data/raw chasm/data/interviews chasm/reports

# Pre-download the embedding model so cold starts are fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

EXPOSE 8000

# Run with uvicorn; Render expects the PORT env var
CMD ["sh", "-c", "uvicorn chasm.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
