# Ryanair Connecting Flight Search

Find one-stop connecting flights on Ryanair between airports that don't have direct routes.

Ryanair doesn't sell connecting tickets, but you can book two separate one-way flights through an intermediate airport. This tool automates finding those connections.

> **Note:** This tool uses Ryanair's unofficial public APIs. It is not affiliated with Ryanair. API responses may change without notice.

## Installation

Requires Python 3.14+.

```bash
# Clone the repo
git clone https://github.com/your-username/ryanair-flight-search.git
cd ryanair-flight-search

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Quick Start

### 1. Discover connection airports

Find which airports connect your origin and destination:

```bash
ryanair-search discover --origin CRV --destination SVQ
```

This saves results to `connections.json` for use by the search command.

### 2. Search for flights

```bash
ryanair-search search --start 2026-03-01 --end 2026-03-07
```

The search command will:
- Load discovered connections from `connections.json` (or use built-in defaults)
- Query available dates for each leg
- Find all valid connecting itineraries
- Sort results by price, then arrival time

## Usage

### `discover` command

```bash
ryanair-search discover [--origin CRV] [--destination SVQ] [--no-cache] [--debug]
```

Finds airports served by both origin and destination, which can be used as connection points.

### `search` command

```bash
ryanair-search search --start YYYY-MM-DD --end YYYY-MM-DD \
    [--origin CRV] [--destination SVQ] \
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
| `--origin` | CRV | Origin airport IATA code |
| `--destination` | SVQ | Destination airport IATA code |
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
ryanair-search search --start 2026-03-01 --end 2026-03-07 --output json > results.json
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
