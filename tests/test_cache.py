"""Tests for SQLite cache."""

import time

from ryanair_flight_search.cache import SQLiteCache


class TestSQLiteCache:
    def setup_method(self, tmp_path=None):
        pass

    def test_get_missing_key(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db")
        assert cache.get("https://example.com") is None

    def test_set_and_get(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db")
        data = {"key": "value", "number": 42}
        cache.set("https://example.com", None, data)
        result = cache.get("https://example.com")
        assert result == data

    def test_set_and_get_with_params(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db")
        data = {"flights": []}
        cache.set("https://example.com/api", {"a": "1", "b": "2"}, data)
        result = cache.get("https://example.com/api", {"a": "1", "b": "2"})
        assert result == data

    def test_different_params_different_keys(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db")
        cache.set("https://example.com", {"a": "1"}, {"data": "first"})
        cache.set("https://example.com", {"a": "2"}, {"data": "second"})
        assert cache.get("https://example.com", {"a": "1"}) == {"data": "first"}
        assert cache.get("https://example.com", {"a": "2"}) == {"data": "second"}

    def test_expiry(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db", expiry_hours=0)
        cache.set("https://example.com", None, {"data": "old"})
        time.sleep(0.01)
        assert cache.get("https://example.com") is None

    def test_overwrite(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db")
        cache.set("https://example.com", None, {"v": 1})
        cache.set("https://example.com", None, {"v": 2})
        assert cache.get("https://example.com") == {"v": 2}

    def test_cleanup(self, tmp_path):
        cache = SQLiteCache(tmp_path / "test.db", expiry_hours=0)
        cache.set("https://example.com/1", None, {"a": 1})
        cache.set("https://example.com/2", None, {"a": 2})
        time.sleep(0.01)
        deleted = cache.cleanup()
        assert deleted == 2
        assert cache.get("https://example.com/1") is None
