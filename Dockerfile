# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# Copy source and install the project
COPY src/ src/
COPY --from=frontend-build /app/frontend/dist src/ryanair_flight_search/webapi/static/
COPY README.md LICENSE ./
RUN uv sync --no-dev --frozen

ENTRYPOINT ["uv", "run", "--no-sync"]
CMD ["ryanair-web", "--host", "0.0.0.0", "--port", "8080"]
