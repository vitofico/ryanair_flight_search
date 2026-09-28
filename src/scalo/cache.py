"""SQLite-based API response cache."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .config import DEFAULT_CACHE_EXPIRY_HOURS
from .exceptions import CacheError

logger = logging.getLogger(__name__)


class SQLiteCache:
    """Simple SQLite-based cache for API responses."""

    def __init__(self, db_path: Path, expiry_hours: int = DEFAULT_CACHE_EXPIRY_HOURS) -> None:
        self.db_path = db_path
        self.expiry_hours = expiry_hours
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
                conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"Failed to initialize cache database: {e}") from e

    def _make_key(self, url: str, params: dict[str, str] | None = None) -> str:
        key_data = url
        if params:
            key_data += "?" + urlencode(sorted(params.items()))
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, url: str, params: dict[str, str] | None = None) -> Any | None:
        key = self._make_key(url, params)
        expiry_threshold = time.time() - (self.expiry_hours * 3600)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT value, created_at FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()

                if row is None:
                    return None

                value, created_at = row
                if created_at < expiry_threshold:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                logger.debug("Cache hit: %s", url)
                return json.loads(value)
        except sqlite3.Error as e:
            logger.warning("Cache read error: %s", e)
            return None

    def set(self, url: str, params: dict[str, str] | None, value: Any) -> None:
        key = self._make_key(url, params)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), time.time()),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("Cache write error: %s", e)

    def cleanup(self) -> int:
        expiry_threshold = time.time() - (self.expiry_hours * 3600)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM cache WHERE created_at < ?", (expiry_threshold,))
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.warning("Cache cleanup error: %s", e)
            return 0
