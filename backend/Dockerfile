# ── Stage 1: Install dependencies with uv ──────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation and copy uv cache into venv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and install project
COPY . .
RUN uv sync --frozen --no-dev

# ── Stage 2: Production runtime ────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install runtime system deps (Playwright needs some libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
        libcairo2 libasound2 && \
    rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Ensure venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

# Copy application code
COPY . .

# Create deployed directory for build outputs
RUN mkdir -p /app/deployed

# Expose FastAPI port
EXPOSE 8000

# Railway sets $PORT dynamically; default to 8000 for local
ENV PORT=8000

# Run uvicorn directly from the venv (uv is not in the runtime image)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
