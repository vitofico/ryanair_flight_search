.DEFAULT_GOAL := help

.PHONY: help install test lint format typecheck check run docker-build

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; print "Usage: make <target>\n"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies, including the dev group
	uv sync --group dev

test: ## Run the tests with the 80% coverage floor
	uv run pytest

lint: ## Lint and verify formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Reformat the code in place
	uv run ruff format .

typecheck: ## Type check in strict mode
	uv run mypy

check: lint typecheck test ## Run every gate CI runs

run: ## Serve the web UI on http://127.0.0.1:8000
	uv run ryanair-web

docker-build: ## Build the Docker image
	docker compose build
