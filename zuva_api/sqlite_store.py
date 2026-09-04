"""Shared SQLite plumbing for the API's stores.

Settings, rate-limit state, sent alerts and telemetry readings all live in the
one file at ``SETTINGS_DB_PATH`` (``/data/zuva.db``). One file means one volume
to mount and one thing to back up; the service is a single process, so a second
database would buy nothing.
"""
import logging
import os
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "/data/zuva.db"


def resolve_db_path(path: str | None = None) -> str:
    """Explicit path wins, then SETTINGS_DB_PATH, then the container default."""
    return path or os.getenv("SETTINGS_DB_PATH", DEFAULT_DB_PATH)


class SqliteStore:
    """Connection and schema handling for a table group in the shared file.

    Subclasses set ``SCHEMA`` to statements that are safe to re-run: every
    store initialises itself at startup, and they share the file.
    """

    SCHEMA = ""

    def __init__(self, path: str | None = None):
        self.path = resolve_db_path(path)

    def initialize(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)
        logger.info("%s ready at %s", type(self).__name__, self.path)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
