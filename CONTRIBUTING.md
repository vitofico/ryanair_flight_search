# Contributing

## Setup

```bash
git clone https://github.com/your-username/ryanair-flight-search.git
cd ryanair-flight-search
uv sync --group dev
```

## Development workflow

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy
```

## Pull requests

1. Create a branch from `main`
2. Make your changes
3. Ensure `pytest`, `ruff check`, and `mypy` pass
4. Open a PR with a clear description

## Code style

- Ruff handles formatting and linting (config in `pyproject.toml`)
- Type hints on all public functions
- Tests for new functionality
