"""Tests for web API security configuration."""

from __future__ import annotations

from starlette.testclient import TestClient

from ryanair_flight_search.webapi.main import app


def test_cors_does_not_reflect_arbitrary_origin() -> None:
    """A hostile site must not receive an ACAO header naming itself."""
    client = TestClient(app)
    response = client.options(
        "/api/v1/airports",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"


def test_cors_does_not_allow_credentials() -> None:
    """Credentialed cross-origin requests must not be permitted."""
    client = TestClient(app)
    response = client.options(
        "/api/v1/airports",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-credentials") != "true"
