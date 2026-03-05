# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Responsive web GUI (FastAPI + React/Vite) accessible via `ryanair-web` command
- Real-time search progress via Server-Sent Events (SSE) with polling fallback
- Airport autocomplete with search by IATA code, city, or country name
- Itinerary comparison page with cross-search selection, summary strip, and export (JSON/CSV)
- Service layer (`services.py`) shared between CLI and web API
- Progress callback support in `FlightSearcher.search()`
- Multi-stage Docker build serving both CLI and web UI
- Active airports API endpoint integration

### Changed
- CLI refactored to thin adapter using shared service layer
- Professional `src/` layout with modular package structure
- SQLite-based API response caching with configurable expiry
- Domain exceptions (`APIError`, `CacheError`, `InvalidRouteError`)
- `discover` command to find valid connection airports for a route
- Structured logging (progress to stderr, output to stdout)
- CLI with argparse subcommands (`discover`, `search`)
- JSON and table output formats
- Configurable connection constraints (min/max time, overnight toggle)
- Connections file persistence (`connections.json`)
- Comprehensive test suite (84% coverage)
- Type checking with mypy (strict mode)
- Linting and formatting with ruff
- Pre-commit hooks configuration
- GitHub Actions CI (lint, typecheck, test, Docker build)
- Dockerfile with uv Python base image
- MIT License, README, and CONTRIBUTING guide
- Centralized configuration in `config.py`

### Removed
- Monolithic single-file script (`ryanair_search.py`)
