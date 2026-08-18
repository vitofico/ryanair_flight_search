# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

LABEL org.opencontainers.image.title="ryanair-flight-search" \
      org.opencontainers.image.description="Find one-stop connecting flights on Ryanair" \
      org.opencontainers.image.source="https://github.com/vitofico/ryanair_flight_search" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# Copy source and install the project
COPY src/ src/
COPY --from=frontend-build /app/frontend/dist src/ryanair_flight_search/webapi/static/
COPY README.md LICENSE ./
RUN uv sync --no-dev --frozen

# Both the SQLite cache and connections.json are written next to the process
# working directory, so /data is where a volume has to land to persist them.
RUN useradd --create-home --uid 1000 app && install -d -o app -g app /data
USER app
WORKDIR /data

# Putting the venv on PATH means both entry points are callable directly, so
# the image serves the web UI by default and still runs the CLI on demand:
#   docker run --rm IMAGE ryanair-search discover --origin DUB --destination SVQ
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
CMD ["ryanair-web", "--host", "0.0.0.0", "--port", "8080"]
