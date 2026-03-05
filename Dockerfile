FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# Copy source and install the project
COPY src/ src/
COPY README.md LICENSE ./
RUN uv sync --no-dev --frozen

ENTRYPOINT ["uv", "run", "--no-sync", "ryanair-search"]
