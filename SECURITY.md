# Security Policy

## Supported versions

This project is pre-1.0. Only the latest commit on `main` is supported. Older tags get no backports.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Use GitHub's private vulnerability reporting:

**https://github.com/vitofico/ryanair_flight_search/security/advisories/new**

Include:

- A description of the issue.
- Steps to reproduce, with a minimal proof of concept if you have one.
- Affected component (CLI, FastAPI backend, React frontend).
- Your assessment of impact.

You will get an acknowledgement within **5 business days**. If the report is accepted, expect a fix or mitigation within **30 days** for high-severity issues, longer for lower-severity ones.

## Scope

In scope:

- Command or code injection through CLI arguments, API parameters, or cached data.
- Path traversal in cache or `connections.json` handling.
- Cross-site scripting or CSRF in the web UI.
- CORS or origin-handling flaws in the FastAPI backend.
- Dependency vulnerabilities with a demonstrated path to exploitation here.

Out of scope, because it is documented behaviour rather than a defect:

- **The web API has no authentication.** This is a local-use tool by design. The README says to run it on `127.0.0.1` and never expose the port. "I published port 8000 to the internet and someone used it" is a deployment choice, not a vulnerability.
- **No rate limiting on the API.** Same reasoning.
- Anything requiring an attacker to already have local filesystem or shell access.
- Reports about Ryanair's own endpoints or infrastructure. Those are not ours; report them to Ryanair.

## A note on the upstream

This tool queries undocumented Ryanair endpoints. If you find a flaw in *their* API while using this project, please report it to Ryanair rather than filing it here or publishing it. Do not use this repository as a vehicle for testing their systems.
