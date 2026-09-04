"""Durable storage for notification settings and rate-limit state.

Settings are configuration, not time series. They used to be read back from
InfluxDB with ``range(start: -1d)``, so a restart more than a day after the last
write silently lost every user's configuration and the service went quiet while
still reporting healthy. Rate-limit timestamps had the same problem in reverse:
being memory-only, a restart re-armed every category and could flood the user.

SQLite gives both durability and simple atomic updates. The file lives on a
mounted volume (``SETTINGS_DB_PATH``) and is shared with the alert and telemetry
history (see ``history_store``).
"""
import logging
from datetime import datetime

from .models import UserSettings
from .sqlite_store import DEFAULT_DB_PATH, SqliteStore

logger = logging.getLogger(__name__)

__all__ = ["DEFAULT_DB_PATH", "SettingsStore"]


class SettingsStore(SqliteStore):
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        enabled_channels TEXT NOT NULL,
        telegram_chat_id TEXT,
        quiet_hours_start TEXT NOT NULL,
        quiet_hours_end TEXT NOT NULL,
        min_severity TEXT NOT NULL,
        rate_limit_minutes INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS alert_state (
        user_id TEXT NOT NULL,
        category TEXT NOT NULL,
        last_sent_at TEXT NOT NULL,
        PRIMARY KEY (user_id, category)
    );
    """

    # -- settings ----------------------------------------------------------

    def save(self, settings: UserSettings) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_settings (user_id, enabled_channels, telegram_chat_id,
                                           quiet_hours_start, quiet_hours_end,
                                           min_severity, rate_limit_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    enabled_channels=excluded.enabled_channels,
                    telegram_chat_id=excluded.telegram_chat_id,
                    quiet_hours_start=excluded.quiet_hours_start,
                    quiet_hours_end=excluded.quiet_hours_end,
                    min_severity=excluded.min_severity,
                    rate_limit_minutes=excluded.rate_limit_minutes
                """,
                (
                    settings.user_id,
                    ",".join(settings.enabled_channels),
                    settings.telegram_chat_id,
                    settings.quiet_hours_start,
                    settings.quiet_hours_end,
                    settings.min_severity,
                    settings.rate_limit_minutes,
                ),
            )

    def load_all(self) -> dict[str, UserSettings]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM user_settings").fetchall()
            state_rows = conn.execute("SELECT * FROM alert_state").fetchall()

        last_alert_times: dict[str, dict[str, datetime]] = {}
        for row in state_rows:
            try:
                when = datetime.fromisoformat(row["last_sent_at"])
            except (TypeError, ValueError):
                continue
            last_alert_times.setdefault(row["user_id"], {})[row["category"]] = when

        settings = {}
        for row in rows:
            channels = [c for c in (row["enabled_channels"] or "").split(",") if c]
            settings[row["user_id"]] = UserSettings(
                user_id=row["user_id"],
                enabled_channels=channels,
                telegram_chat_id=row["telegram_chat_id"] or None,
                quiet_hours_start=row["quiet_hours_start"],
                quiet_hours_end=row["quiet_hours_end"],
                min_severity=row["min_severity"],
                rate_limit_minutes=row["rate_limit_minutes"],
                last_alert_times=last_alert_times.get(row["user_id"], {}),
            )
        return settings

    # -- rate limiting -----------------------------------------------------

    def record_alert(self, user_id: str, category: str, when: datetime) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_state (user_id, category, last_sent_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, category) DO UPDATE SET
                    last_sent_at=excluded.last_sent_at
                """,
                (user_id, category, when.isoformat()),
            )
