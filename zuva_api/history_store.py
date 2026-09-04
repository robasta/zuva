"""Durable storage for sent alerts and inverter telemetry.

Both were InfluxDB measurements. Nothing ever read the telemetry series back,
the alert history is a lookup by user and time range, and at one reading per
poll the whole data set is a few megabytes a year - so the time-series database
was a container, two volumes and two secrets spent on a table scan. Both live in
SQLite now, next to the settings.

Timestamps are stored as UTC ISO-8601 strings. ISO strings only sort
lexicographically while every row shares one offset, and both the history query
and the retention sweep compare them with ``>=``; storing UTC keeps that true
even if ``TIMEZONE`` changes. Values are converted back to local time on the way
out, so callers still see the site's clock.
"""
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from .sqlite_store import SqliteStore
from .timeutil import get_timezone, local_now

logger = logging.getLogger(__name__)

# Telemetry is written every poll, so something has to delete it. This replaces
# the InfluxDB bucket retention that used to do the job.
RETENTION_DAYS = int(os.getenv("HISTORY_RETENTION_DAYS", "90"))

# A long-lived container would otherwise only prune at startup.
PRUNE_INTERVAL_SECONDS = 6 * 3600

READING_COLUMNS = (
    "inverter_sn",
    "plant_id",
    "load_power_w",
    "grid_power_w",
    "battery_soc",
    "grid_voltage",
    "grid_status",
    "battery_power_w",
    "battery_voltage",
    "input_power_w",
)


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=get_timezone())
    return value.astimezone(timezone.utc).isoformat()


def _from_utc_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(get_timezone())


class HistoryStore(SqliteStore):
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sent_at TEXT NOT NULL,
        user_id TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS alerts_user_sent_at ON alerts (user_id, sent_at);
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at TEXT NOT NULL,
        inverter_sn TEXT NOT NULL,
        plant_id TEXT,
        load_power_w REAL,
        grid_power_w REAL,
        battery_soc REAL,
        grid_voltage REAL,
        grid_status INTEGER,
        battery_power_w REAL,
        battery_voltage REAL,
        input_power_w REAL
    );
    CREATE INDEX IF NOT EXISTS readings_recorded_at ON readings (recorded_at);
    """

    def __init__(self, path: str | None = None, retention_days: int | None = None):
        super().__init__(path)
        self.retention_days = RETENTION_DAYS if retention_days is None else retention_days
        self._last_prune = None

    def initialize(self) -> None:
        super().initialize()
        # A restart is a good moment to drop what has aged out.
        self.prune()

    # -- alerts ------------------------------------------------------------

    def record_alert(
        self,
        user_id: str,
        category: str,
        severity: str,
        title: str,
        message: str,
        when: datetime | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alerts (sent_at, user_id, category, severity, title, message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    _to_utc_iso(when or local_now()),
                    user_id,
                    category,
                    severity,
                    title,
                    message,
                ),
            )

    def recent_alerts(self, user_id: str, hours: int) -> list[dict]:
        """Alerts sent to ``user_id`` in the last ``hours``, newest first."""
        since = _to_utc_iso(local_now() - timedelta(hours=hours))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT sent_at, category, severity, title, message
                FROM alerts
                WHERE user_id = ? AND sent_at >= ?
                ORDER BY sent_at DESC
                """,
                (user_id, since),
            ).fetchall()
        return [
            {
                "time": _from_utc_iso(row["sent_at"]),
                "category": row["category"],
                "severity": row["severity"],
                "title": row["title"],
                "message": row["message"],
            }
            for row in rows
        ]

    # -- telemetry ---------------------------------------------------------

    def record_reading(self, recorded_at: datetime | None = None, **fields) -> None:
        unknown = set(fields) - set(READING_COLUMNS)
        if unknown:
            raise ValueError(f"unknown reading fields: {sorted(unknown)}")

        columns = ["recorded_at", *fields]
        values = [_to_utc_iso(recorded_at or local_now()), *fields.values()]
        placeholders = ", ".join("?" for _ in columns)
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO readings ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        self._maybe_prune()

    # -- retention ---------------------------------------------------------

    def prune(self, retention_days: int | None = None) -> int:
        """Delete rows older than the retention window; returns rows removed."""
        days = self.retention_days if retention_days is None else retention_days
        if days <= 0:
            return 0
        cutoff = _to_utc_iso(local_now() - timedelta(days=days))
        with self._connect() as conn:
            removed = conn.execute(
                "DELETE FROM readings WHERE recorded_at < ?", (cutoff,)
            ).rowcount
            removed += conn.execute(
                "DELETE FROM alerts WHERE sent_at < ?", (cutoff,)
            ).rowcount
        self._last_prune = time.monotonic()
        if removed:
            logger.info("Pruned %s rows older than %s days", removed, days)
        return removed

    def _maybe_prune(self) -> None:
        # None, not 0.0: time.monotonic() counts from boot, so a 0.0 sentinel
        # would skip the first sweep on a freshly started host.
        if self._last_prune is not None and time.monotonic() - self._last_prune < PRUNE_INTERVAL_SECONDS:
            return
        try:
            self.prune()
        except Exception as error:  # pylint: disable=broad-except
            # Retention housekeeping must never lose the reading being written.
            logger.error("Could not prune history: %s", error)
            self._last_prune = time.monotonic()
