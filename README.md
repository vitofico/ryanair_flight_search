# Ryanair Connecting Flight Search

Find one-stop connecting flights on Ryanair between airports that don't have direct routes.

Ryanair doesn't sell connecting tickets, but you can book two separate one-way flights through an intermediate airport. This tool automates finding those connections.

## Disclaimer

This is an independent personal project, built for personal and educational use. It is **not affiliated with, endorsed by, or connected to Ryanair** in any way.

It works by querying Ryanair's undocumented public JSON endpoints, the same ones their website calls. Those endpoints are not a supported API: they can change or disappear without notice, and using them may conflict with Ryanair's Terms of Use. You are responsible for deciding whether your use is appropriate, and for using the tool at a reasonable request volume. The software is provided without warranty of any kind, and the author accepts no liability for how it is used.

Itineraries found here are **two separately booked one-way flights**, not a protected connection. If the first leg is delayed or cancelled, you have no rebooking rights on the second, and no compensation claim for the missed connection. Leave a generous layover and understand you are carrying that risk yourself.

## Installation

Requires Python 3.11+.

```bash
# Clone the repo
git clone https://github.com/vitofico/ryanair_flight_search.git
cd ryanair_flight_search

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Quick Start

### 1. Discover connection airports

Find which airports connect your origin and destination:

```bash
ryanair-search discover --origin DUB --destination SVQ
```

This saves results to `connections.json` for use by the search command.

### 2. Search for flights

```bash
ryanair-search search --origin DUB --destination SVQ --start 2026-03-01 --end 2026-03-07
```

`--origin` and `--destination` are required on both commands.

The search command will:
- Load discovered connections from `connections.json`, unless you pass `--connections`
- Query available dates for each leg
- Find all valid connecting itineraries
- Sort results by price, then arrival time

## Web UI

Run the backend and frontend dev server in two terminals:

```bash
# Terminal 1: API server (port 8000)
uv run ryanair-web

# Terminal 2: Vite dev server (port 5173)
cd frontend && npm run dev
```

Open http://localhost:5173.

For production, build the frontend and serve everything from the backend:

```bash
cd frontend && npm run build
uv run ryanair-web
```

Then open http://localhost:8000.

> **Run this locally only.** The web API has no authentication and no rate limiting, and a single search fans out hundreds of outbound requests to Ryanair. If you expose the port to a network, anyone who can reach it can drive that traffic from your IP address. The CLI entry point binds to `127.0.0.1` by default; note that the Docker image binds `0.0.0.0` so the container is reachable, so publish that port only on a trusted host.

## Usage

### `discover` command

```bash
ryanair-search discover --origin DUB --destination SVQ [--no-cache] [--debug]
```

Finds airports served by both origin and destination, which can be used as connection points.

### `search` command

```bash
ryanair-search search --origin DUB --destination SVQ \
    --start YYYY-MM-DD --end YYYY-MM-DD \
    [--connections BGY,BLQ] \
    [--currency EUR] \
    [--min-connection-minutes 60] \
    [--max-connection-hours 8] \
    [--allow-overnight] \
    [--output table|json] \
    [--no-cache] [--debug]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--start` | required | Start of date range |
| `--end` | required | End of date range |
| `--origin` | required | Origin airport IATA code |
| `--destination` | required | Destination airport IATA code |
| `--connections` | auto | Comma-separated connection airports |
| `--currency` | EUR | Currency for prices |
| `--min-connection-minutes` | 60 | Minimum layover time |
| `--max-connection-hours` | 8 | Maximum layover time |
| `--allow-overnight` | false | Allow next-day connections |
| `--output` | table | Output format: `table` or `json` |
| `--no-cache` | false | Disable response caching |
| `--debug` | false | Show debug output |

### Output formats

**Table** (default): Human-readable table to terminal.

**JSON**: Machine-readable output to stdout (progress messages go to stderr), suitable for piping:

```bash
ryanair-search search --origin DUB --destination SVQ \
    --start 2026-03-01 --end 2026-03-07 --output json > results.json
```

## Caching

API responses are cached in a local SQLite database (`ryanair_cache.db`) for 6 hours to reduce API calls and speed up repeated searches. Use `--no-cache` to bypass.

## Architecture

```
src/ryanair_flight_search/
  cli.py          - Command-line interface and argument parsing
  api_client.py   - Ryanair API client with retries and rate limiting
  cache.py        - SQLite-based response cache
  search.py       - Search orchestration
  itinerary.py    - Itinerary builder and connection validation
  models.py       - Flight and Itinerary data models
  output.py       - Table and JSON output formatters
  exceptions.py   - Domain exception types
  webapi/         - FastAPI backend for the web UI
frontend/         - React + Vite frontend
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy
```

## License

MIT
