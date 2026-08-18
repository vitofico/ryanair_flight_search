<h1 align="center">Ryanair Connecting Flight Search</h1>

<p align="center">
  <em>Ryanair won't sell you a connecting ticket.<br>
  This finds the two flights that make one anyway.</em>
</p>

<p align="center">
  <a href="https://github.com/vitofico/ryanair_flight_search/actions/workflows/ci.yml"><img src="https://github.com/vitofico/ryanair_flight_search/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+">
</p>

## What it is

Say you want to get from Dublin to Seville. Ryanair flies both routes through Milan Bergamo, but it will not sell you Dublin to Seville as one ticket, and searching its site just tells you there are no flights.

There are flights. They are simply two bookings that nobody is joining up for you. This tool does the joining: it finds airports served from both ends, prices each leg separately across a date range, keeps only the pairs that actually connect in time, and ranks what survives by total cost.

Two surfaces, same engine:

- **CLI** for scripted or repeatable searches, with JSON output for piping.
- **Web UI** (React + FastAPI) for browsing results as they stream in.

```
        ┌── discover ──> airports served from BOTH ends
        │
DUB ────┤   BGY  BLQ  STN  ...        ← candidate stopovers
        │
        └── search ────> price leg 1 + leg 2 per day, keep valid connections
                              │
                              ▼
                    ranked by total price
```

> [!IMPORTANT]
> These are **two separately booked one-way flights**, not a protected connection. If the first leg is delayed or cancelled, you have no rebooking rights on the second and no compensation claim for the missed connection. Leave a generous layover and understand you are carrying that risk yourself.

## Contents

- [Disclaimer](#disclaimer)
- [Install](#install)
- [Quick start](#quick-start)
- [Web UI](#web-ui)
- [Command reference](#command-reference)
- [How it works](#how-it-works)
- [Caching](#caching)
- [Development](#development)
- [License](#license)

## Disclaimer

This is an independent personal project, built for personal and educational use. It is **not affiliated with, endorsed by, or connected to Ryanair** in any way.

It queries Ryanair's undocumented public JSON endpoints, the same ones their website calls. Those endpoints are not a supported API: they can change or disappear without notice, and using them may conflict with Ryanair's Terms of Use. You are responsible for deciding whether your use is appropriate, and for keeping request volume reasonable. The software is provided without warranty of any kind, and the author accepts no liability for how it is used.

## Install

Requires Python 3.11 or newer.

```bash
git clone https://github.com/vitofico/ryanair_flight_search.git
cd ryanair_flight_search

uv sync          # recommended
# or
pip install -e .
```

## Quick start

### 1. Find the candidate stopovers

Work out which airports Ryanair serves from **both** your origin and your destination:

```bash
ryanair-search discover --origin DUB --destination SVQ
```

Results are saved to `connections.json`, which `search` picks up automatically.

### 2. Search

```bash
ryanair-search search --origin DUB --destination SVQ \
    --start 2026-03-01 --end 2026-03-07
```

```
========================================================================================================================
  # | First Leg                      | Connection   | Second Leg                     |      Total |   Duration
------------------------------------------------------------------------------------------------------------------------
  1 | DUB->BGY 03/03 06:20-10:05     | BGY (3h 10m) | BGY->SVQ 03/03 13:15-15:40     |  EUR 74.98 |     9h 20m
  2 | DUB->STN 03/05 09:15-10:45     | STN (3h 20m) | STN->SVQ 03/05 14:05-17:50     |  EUR 81.50 |     8h 35m
========================================================================================================================
Total: 2 itineraries
```

`--origin` and `--destination` are required on both commands.

## Web UI

```bash
# Terminal 1: API on :8000
uv run ryanair-web

# Terminal 2: Vite dev server on :5173
cd frontend && npm run dev
```

Open http://localhost:5173. Progress streams over SSE, so long searches report as they go rather than blocking on a spinner.

To run it as one process, build the frontend and let the backend serve it:

```bash
cd frontend && npm run build
uv run ryanair-web       # now serves UI + API on :8000
```

> [!WARNING]
> **Run this locally only.** The web API has no authentication and no rate limiting, and one search fans out hundreds of outbound requests to Ryanair. Anyone who can reach the port can drive that traffic from your IP address. The CLI binds `127.0.0.1` by default; the Docker image binds `0.0.0.0`, so publish that port only on a trusted host.

## Command reference

### `discover`

```bash
ryanair-search discover --origin DUB --destination SVQ [--no-cache] [--debug]
```

Intersects the destination lists of both airports to produce the candidate stopovers.

### `search`

```bash
ryanair-search search --origin DUB --destination SVQ \
    --start YYYY-MM-DD --end YYYY-MM-DD \
    [--connections BGY,BLQ] [--currency EUR] \
    [--min-connection-minutes 60] [--max-connection-hours 8] \
    [--allow-overnight] [--output table|json] \
    [--no-cache] [--debug]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--origin` | **required** | Origin airport IATA code |
| `--destination` | **required** | Destination airport IATA code |
| `--start` | **required** | Start of date range |
| `--end` | **required** | End of date range |
| `--connections` | auto | Comma-separated stopovers, overriding `connections.json` |
| `--currency` | `EUR` | Currency for prices |
| `--min-connection-minutes` | `60` | Shortest acceptable layover |
| `--max-connection-hours` | `8` | Longest acceptable layover |
| `--allow-overnight` | `false` | Allow the second leg to depart the next day |
| `--output` | `table` | `table` for humans, `json` for scripts |
| `--no-cache` | `false` | Bypass the response cache |
| `--debug` | `false` | Show debug output |

Results go to stdout and progress to stderr, so JSON pipes cleanly:

```bash
ryanair-search search --origin DUB --destination SVQ \
    --start 2026-03-01 --end 2026-03-07 --output json > results.json
```

## How it works

1. **Route discovery.** Ryanair publishes the destinations served from each airport. Intersecting the origin's list with the destination's gives the airports that could act as a stopover.
2. **Availability.** For each leg the tool asks which dates actually have service, so it never spends requests pricing empty days.
3. **Fares.** Each remaining day is priced one request at a time, throttled to stay polite, with responses cached.
4. **Connection building.** A pair survives only when the second leg departs after the first arrives, inside your layover bounds, same day unless `--allow-overnight`.
5. **Ranking.** Survivors are sorted by total price, then by arrival time.

## Caching

Responses land in a local SQLite database (`ryanair_cache.db`) with a 6 hour TTL. Repeat searches are near-instant and cost Ryanair nothing. Use `--no-cache` to force fresh data.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

```bash
uv sync --group dev
uv run pytest          # 74 tests, 80% coverage floor
uv run ruff check .    # lint
uv run ruff format .   # format
uv run mypy            # strict type check
```

```
src/ryanair_flight_search/
  cli.py          Command-line interface and argument parsing
  api_client.py   Ryanair HTTP client with retries and rate limiting
  cache.py        SQLite response cache
  search.py       Search orchestration
  itinerary.py    Itinerary builder and connection validation
  models.py       Flight and Itinerary data models
  output.py       Table and JSON formatters
  exceptions.py   Domain exception types
  webapi/         FastAPI backend (routers, SSE job manager)
frontend/         React + Vite frontend
```

## License

MIT. See [LICENSE](LICENSE).
