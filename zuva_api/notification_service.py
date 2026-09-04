import logging
import os
from datetime import datetime, timedelta

from influxdb_client import Point

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:  # pragma: no cover - exercised via tests in environments without telegram
    Bot = None

    class TelegramError(Exception):
        pass

from .db import get_influx_client, get_query_api, get_write_api, INFLUXDB_BUCKET
from .models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    NotificationChannel,
    NotificationSettings,
    SEVERITY_ORDER,
    UserSettings,
)
from .settings_store import SettingsStore
from .timeutil import get_timezone, local_now

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")

SEVERITY_EMOJI = {
    AlertSeverity.LOW: "ℹ️",
    AlertSeverity.MEDIUM: "⚠️",
    AlertSeverity.HIGH: "🔥",
    AlertSeverity.CRITICAL: "🚨",
}

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, settings_store: SettingsStore | None = None):
        self.influx_client = None
        self.write_api = None
        self.query_api = None
        self.telegram_bot = None
        self.user_settings = {}
        self.settings_store = settings_store or SettingsStore()

    async def initialize(self):
        self.influx_client = get_influx_client()
        self.write_api = get_write_api(self.influx_client)
        self.query_api = get_query_api(self.influx_client)
        if TELEGRAM_BOT_TOKEN and Bot is not None:
            self.telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logger.info("Telegram bot initialized")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set - Telegram notifications disabled")
        await self._load_user_settings()

    async def _load_user_settings(self):
        try:
            self.settings_store.initialize()
            self.user_settings = self.settings_store.load_all()
            logger.info("Loaded settings for %s users", len(self.user_settings))
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error loading user settings: %s", error)
            self.user_settings = {}

        if not self.user_settings:
            # One-time migration for deployments whose settings only exist in
            # InfluxDB (where they were previously stored).
            self._import_legacy_settings()

        self._ensure_default_user()

    def _import_legacy_settings(self):
        if self.query_api is None:
            return
        query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "user_settings")
                |> last()
        '''
        try:
            result = self.query_api.query(query=query)
        except Exception as error:  # pylint: disable=broad-except
            logger.warning("Could not read legacy settings from InfluxDB: %s", error)
            return

        imported = 0
        for table in result:
            for record in table.records:
                user_id = record.values.get("user_id")
                if not user_id:
                    continue
                settings = UserSettings(
                    user_id=user_id,
                    enabled_channels=[
                        c for c in (record.values.get("enabled_channels") or "").split(",") if c
                    ],
                    telegram_chat_id=record.values.get("telegram_chat_id"),
                    quiet_hours_start=record.values.get("quiet_hours_start") or "22:00",
                    quiet_hours_end=record.values.get("quiet_hours_end") or "07:00",
                    min_severity=record.values.get("min_severity") or "medium",
                    rate_limit_minutes=int(record.values.get("rate_limit_minutes") or 15),
                )
                self.user_settings[user_id] = settings
                self._persist(settings)
                imported += 1
        if imported:
            logger.info("Migrated %s user settings from InfluxDB into the settings store", imported)

    def _ensure_default_user(self):
        if DEFAULT_USER_ID in self.user_settings:
            return
        if not (TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN):
            logger.warning(
                "No settings for default user %r and no TELEGRAM_CHAT_ID/TELEGRAM_BOT_TOKEN "
                "to derive them from; alerts for this user will be rejected",
                DEFAULT_USER_ID,
            )
            return
        default_settings = UserSettings(
            user_id=DEFAULT_USER_ID,
            enabled_channels=[NotificationChannel.TELEGRAM.value],
            telegram_chat_id=TELEGRAM_CHAT_ID,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            min_severity="medium",
            rate_limit_minutes=15,
        )
        self.user_settings[DEFAULT_USER_ID] = default_settings
        self._persist(default_settings)
        logger.info("Auto-configured default user %r from environment variables", DEFAULT_USER_ID)

    def _persist(self, settings: UserSettings):
        try:
            self.settings_store.save(settings)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Could not persist settings for %s: %s", settings.user_id, error)

    async def save_user_settings(self, settings: NotificationSettings):
        existing = self.user_settings.get(settings.user_id)
        user_settings = UserSettings(
            user_id=settings.user_id,
            enabled_channels=[ch.value for ch in settings.enabled_channels],
            telegram_chat_id=settings.telegram_chat_id,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            min_severity=settings.min_severity.value,
            rate_limit_minutes=settings.rate_limit_minutes,
            last_alert_times=dict(existing.last_alert_times) if existing else {},
        )
        self.user_settings[settings.user_id] = user_settings
        self._persist(user_settings)
        logger.info("Saved settings for user %s", settings.user_id)

    # -- filters -----------------------------------------------------------

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=get_timezone())
        return value

    def _is_quiet_hours(self, settings: UserSettings) -> bool:
        now = local_now().time()
        try:
            start = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
        except (TypeError, ValueError):
            logger.error(
                "Invalid quiet hours for %s (%r-%r); treating as disabled",
                settings.user_id,
                settings.quiet_hours_start,
                settings.quiet_hours_end,
            )
            return False
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end

    def _should_rate_limit(self, settings: UserSettings, category: str) -> bool:
        if category not in settings.last_alert_times:
            return False
        last_alert = self._as_aware(settings.last_alert_times[category])
        return local_now() - last_alert < timedelta(minutes=settings.rate_limit_minutes)

    def _severity_check(self, alert_severity, min_severity: str) -> bool:
        alert_value = getattr(alert_severity, "value", alert_severity)
        if alert_value not in SEVERITY_ORDER:
            logger.error("Unknown alert severity %r; allowing the alert through", alert_value)
            return True
        if min_severity not in SEVERITY_ORDER:
            logger.error(
                "Unknown configured min_severity %r; falling back to %r",
                min_severity,
                AlertSeverity.MEDIUM.value,
            )
            min_severity = AlertSeverity.MEDIUM.value
        return SEVERITY_ORDER.index(alert_value) >= SEVERITY_ORDER.index(min_severity)

    # -- sending -----------------------------------------------------------

    async def send_alert(self, alert: Alert, user_id: str = DEFAULT_USER_ID) -> dict:
        """Deliver an alert, returning what was decided.

        Returns ``{"status": "sent"|"suppressed"|"unknown_user"|"failed"}`` so
        the caller can distinguish "deliberately filtered" from "nobody to send
        it to", which used to be an indistinguishable silent drop.
        """
        if alert.category == AlertCategory.BATTERY_CRITICAL and alert.severity != AlertSeverity.CRITICAL:
            alert = alert.model_copy(update={"severity": AlertSeverity.CRITICAL})

        settings = self.user_settings.get(user_id)
        if not settings:
            logger.error(
                "No notification settings for user %r - alert %s was NOT delivered",
                user_id,
                alert.category.value,
            )
            return {"status": "unknown_user", "reason": f"no settings configured for user {user_id}"}

        if not self._severity_check(alert.severity, settings.min_severity):
            logger.info("Alert %s below minimum severity threshold", alert.category.value)
            return {"status": "suppressed", "reason": "below_min_severity"}

        if alert.severity != AlertSeverity.CRITICAL and self._is_quiet_hours(settings):
            logger.info("Skipping alert %s during quiet hours", alert.category.value)
            return {"status": "suppressed", "reason": "quiet_hours"}

        if self._should_rate_limit(settings, alert.category.value):
            logger.info("Rate limiting alert %s", alert.category.value)
            return {"status": "suppressed", "reason": "rate_limited"}

        if not settings.enabled_channels:
            logger.error("User %r has no enabled notification channels", user_id)
            return {"status": "failed", "reason": "no_enabled_channels"}

        success = False
        for channel in settings.enabled_channels:
            if channel == NotificationChannel.TELEGRAM.value:
                if await self._send_telegram(alert, settings):
                    success = True

        if not success:
            return {"status": "failed", "reason": "all_channels_failed"}

        # Only stamp the rate-limit clock once something was actually delivered,
        # so a Telegram outage does not consume the user's alert window.
        sent_at = local_now()
        settings.last_alert_times[alert.category.value] = sent_at
        try:
            self.settings_store.record_alert(user_id, alert.category.value, sent_at)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Could not persist rate-limit state: %s", error)
        self._record_alert_history(alert, user_id)
        return {"status": "sent"}

    def _record_alert_history(self, alert: Alert, user_id: str):
        if self.write_api is None:
            return
        try:
            point = Point("alerts") \
                .tag("user_id", user_id) \
                .tag("category", alert.category.value) \
                .tag("severity", alert.severity.value) \
                .field("title", alert.title) \
                .field("message", alert.message)
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Could not write alert history: %s", error)

    async def _send_telegram(self, alert: Alert, settings: UserSettings) -> bool:
        if not self.telegram_bot or not settings.telegram_chat_id:
            logger.warning("Telegram not configured for this user")
            return False
        try:
            emoji = SEVERITY_EMOJI.get(alert.severity, "🔔")
            message = f"{emoji} **{alert.title}**\n\n{alert.message}"
            if alert.metadata:
                message += "\n\n📊 Details:\n"
                for key, value in alert.metadata.items():
                    message += f"• {key}: {value}\n"
            response = await self.telegram_bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message
            )
            logger.info(
                "Sent Telegram alert to %s (message_id=%s)",
                settings.telegram_chat_id,
                getattr(response, "message_id", None),
            )
            return True
        except TelegramError as error:
            logger.error("Telegram error: %s", error)
            return False

    async def shutdown(self):
        if self.influx_client:
            self.influx_client.close()
