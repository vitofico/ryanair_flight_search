# Contributing

Thanks for taking an interest. This is a small personal project, so please read this before opening a PR.

## Ground rules

- **Scope is deliberately narrow.** This finds self-transfer itineraries on Ryanair. PRs adding other airlines, booking automation, or payment flows are out of scope and will be closed.
- **Stay polite to the upstream.** The tool talks to undocumented endpoints that Ryanair does not owe us. Anything that raises request volume, removes the throttle, adds concurrency against their API, or works around blocking will not be merged. If you make the tool faster, make it by sending *fewer* requests, not more.
- **No credential handling.** The tool needs no login and should never grow one.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/vitofico/ryanair_flight_search.git
cd ryanair_flight_search
uv sync --group dev
```

For the frontend:

```bash
cd frontend && npm install
```

Optional but recommended, the repo ships a pre-commit config:

```bash
uv tool install pre-commit
pre-commit install
```

## The checks

All four must pass before a PR is merged. CI runs the same set.

```bash
uv run pytest              # tests, with an 80% coverage floor
uv run ruff check .        # lint
uv run ruff format --check .
uv run mypy                # strict mode, no untyped defs
```

`uv run ruff format .` fixes formatting in place.

## Tests

- New behaviour needs a test. Bug fixes need a regression test that fails before the fix.
- Never hit the live Ryanair API from a test. Mock at the `api_client` boundary; `tests/conftest.py` has the fixtures.
- Coverage must stay at or above 80%, enforced by `--cov-fail-under=80`. The `webapi/` package is excluded from coverage, so backend routes are tested through behaviour rather than line count.

## Pull requests

- Branch from `main`, one topic per PR.
- Keep diffs reviewable. Under ~400 lines is ideal.
- Update the README and `CHANGELOG.md` in the same PR as the code. Stale docs are worse than missing docs.
- If you change CLI flags or output format, update the command reference table in the README.

## Commit messages

Gitmoji + conventional commits. The emoji goes after the type, before the colon-space:

```
:sparkles: feat(search): add --allow-overnight for next-day connections
:bug: fix(api): handle 429 without retrying past the backoff budget
:memo: docs: correct the layover defaults in the command table
:white_check_mark: test(itinerary): cover the same-airport rejection path
:construction_worker: ci: pin actions to commit SHAs
:wrench: chore: bump ruff to 0.9
```

Common gitmoji here: `:sparkles:` (feat), `:bug:` (fix), `:memo:` (docs),
`:white_check_mark:` (tests), `:construction_worker:` (CI), `:wrench:` (chore),
`:art:` (refactor/style), `:fire:` (removals), `:lock:` (security),
`:page_facing_up:` (legal/license), `:whale:` (Docker).

Types in use: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`, `style`.

## Reporting bugs

Open an issue with the command you ran, the full output with `--debug`, and your Python version. If the tool suddenly returns nothing for a route that used to work, that is usually Ryanair changing an endpoint shape rather than a regression here; say so in the report and include the raw response if you can capture it.

For security issues, see [SECURITY.md](SECURITY.md); please do not open a public issue.
