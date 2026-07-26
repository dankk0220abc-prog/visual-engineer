FROM ghcr.io/astral-sh/uv:0.11.30 AS uv

FROM python:3.12.13-slim-bookworm AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12.13-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/apps/runner/src:/app/packages/runner-protocol/src"
RUN apt-get update \
  && apt-get install --yes --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --system --gid 10001 runner \
  && useradd --system --uid 10001 --gid runner --no-create-home runner \
  && mkdir -p \
    /var/lib/visual-engineer-runner/mirrors \
    /var/lib/visual-engineer-runner/workspaces \
    /var/lib/visual-engineer-runner/registry \
  && chown -R runner:runner /var/lib/visual-engineer-runner
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY packages/runner-protocol/src packages/runner-protocol/src
COPY apps/runner/src apps/runner/src
USER runner
CMD ["python", "-m", "visual_engineer_runner.main"]
