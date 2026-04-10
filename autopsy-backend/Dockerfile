FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" VIRTUAL_ENV="/app/.venv"
COPY . .
RUN mkdir -p /tmp/code-autopsy
EXPOSE 8001
ENV PORT=8001
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
