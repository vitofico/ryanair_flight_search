"""Tests for CLI."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ryanair_flight_search.cli import (
    _build_cache,
    cmd_search,
    load_connections,
    main,
    parse_args,
    save_connections,
    validate_date,
)


class TestParseArgs:
    def test_discover_defaults(self):
        args = parse_args(["discover"])
        assert args.command == "discover"
        assert args.origin == ""
        assert args.destination == ""
        assert args.debug is False

    def test_discover_custom(self):
        args = parse_args(["discover", "--origin", "STN", "--destination", "MAD"])
        assert args.origin == "STN"
        assert args.destination == "MAD"

    def test_search_required_args(self):
        args = parse_args(["search", "--start", "2026-03-01", "--end", "2026-03-07"])
        assert args.command == "search"
        assert args.start == "2026-03-01"
        assert args.end == "2026-03-07"

    def test_search_all_options(self):
        args = parse_args(
            [
                "search",
                "--start",
                "2026-03-01",
                "--end",
                "2026-03-07",
                "--origin",
                "STN",
                "--destination",
                "MAD",
                "--connections",
                "BGY,CRL",
                "--currency",
                "GBP",
                "--output",
                "json",
                "--debug",
            ]
        )
        assert args.origin == "STN"
        assert args.connections == "BGY,CRL"
        assert args.currency == "GBP"
        assert args.output == "json"
        assert args.debug is True

    def test_missing_command_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_search_missing_dates_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["search"])


class TestValidateDate:
    def test_valid_date(self):
        result = validate_date("2026-03-10", "start")
        assert result == date(2026, 3, 10)

    def test_invalid_date_exits(self):
        with pytest.raises(SystemExit):
            validate_date("not-a-date", "start")


class TestConnections:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ryanair_flight_search.cli._connections_path",
            lambda: tmp_path / "connections.json",
        )

        save_connections("CRV", "SVQ", ["BGY", "BLQ"])
        result = load_connections("CRV", "SVQ")
        assert result == ["BGY", "BLQ"]

    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ryanair_flight_search.cli._connections_path",
            lambda: tmp_path / "nonexistent.json",
        )
        assert load_connections("CRV", "SVQ") is None

    def test_load_wrong_route(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ryanair_flight_search.cli._connections_path",
            lambda: tmp_path / "connections.json",
        )
        save_connections("CRV", "SVQ", ["BGY"])
        assert load_connections("STN", "MAD") is None

    def test_load_corrupt_file(self, tmp_path, monkeypatch):
        path = tmp_path / "connections.json"
        path.write_text("not valid json")
        monkeypatch.setattr(
            "ryanair_flight_search.cli._connections_path",
            lambda: path,
        )
        assert load_connections("CRV", "SVQ") is None

    def test_save_over_corrupt_file(self, tmp_path, monkeypatch):
        path = tmp_path / "connections.json"
        path.write_text("not valid json")
        monkeypatch.setattr(
            "ryanair_flight_search.cli._connections_path",
            lambda: path,
        )
        save_connections("CRV", "SVQ", ["BGY"])
        result = load_connections("CRV", "SVQ")
        assert result == ["BGY"]


class TestBuildCache:
    def test_no_cache(self):
        assert _build_cache(no_cache=True) is None

    def test_with_cache(self, tmp_path, monkeypatch):

        monkeypatch.chdir(tmp_path)
        cache = _build_cache(no_cache=False)
        assert cache is not None


class TestMain:
    def test_main_discover(self, monkeypatch):
        with patch("ryanair_flight_search.cli.cmd_discover") as mock:
            main(["discover"])
            mock.assert_called_once()

    def test_main_search(self, monkeypatch):
        with patch("ryanair_flight_search.cli.cmd_search") as mock:
            main(["search", "--start", "2026-03-01", "--end", "2026-03-07"])
            mock.assert_called_once()


class TestCmdSearch:
    def test_start_after_end_exits(self):
        args = parse_args(["search", "--start", "2026-03-10", "--end", "2026-03-01"])
        with pytest.raises(SystemExit):
            cmd_search(args)

    def test_search_with_explicit_connections(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []
        with (
            patch("ryanair_flight_search.cli.FlightSearcher", return_value=mock_searcher),
            patch("ryanair_flight_search.cli.RyanairAPIClient"),
        ):
            args = parse_args(
                [
                    "search",
                    "--start",
                    "2026-03-10",
                    "--end",
                    "2026-03-10",
                    "--connections",
                    "BGY",
                    "--no-cache",
                ]
            )
            cmd_search(args)
            mock_searcher.search.assert_called_once()
