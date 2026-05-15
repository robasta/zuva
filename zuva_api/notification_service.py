import logging
import os
from datetime import datetime
from influxdb_client import Point

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:  # pragma: no cover - exercised via tests in environments without telegram
    Bot = None

    class TelegramError(Exception):
        pass
from .models import NotificationChannel, AlertSeverity, AlertCategory, NotificationSettings, Alert, UserSettings
from .db import get_influx_client, get_write_api, get_query_api, INFLUXDB_BUCKET

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.query_api = None
        self.telegram_bot = None
        self.user_settings = {}
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
            query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: -1d)
                    |> filter(fn: (r) => r._measurement == "user_settings")
                    |> last()
            '''
            result = self.query_api.query(query=query)
            for table in result:
                for record in table.records:
                    user_id = record.values.get("user_id")
                    if user_id:
                        settings = UserSettings(
                            user_id=user_id,
                            enabled_channels=record.values.get("enabled_channels", "").split(","),
                            telegram_chat_id=record.values.get("telegram_chat_id"),
                            quiet_hours_start=record.values.get("quiet_hours_start", "22:00"),
                            quiet_hours_end=record.values.get("quiet_hours_end", "07:00"),
                            min_severity=record.values.get("min_severity", "medium"),
                            rate_limit_minutes=int(record.values.get("rate_limit_minutes", 15))
                        )
                        self.user_settings[user_id] = settings
            logger.info(f"Loaded settings for {len(self.user_settings)} users")
            if DEFAULT_USER_ID not in self.user_settings:
                enabled_channels = []
                if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
                    enabled_channels.append("telegram")
                if enabled_channels:
                    default_settings = UserSettings(
                        user_id=DEFAULT_USER_ID,
                        enabled_channels=enabled_channels,
                        telegram_chat_id=TELEGRAM_CHAT_ID,
                        quiet_hours_start="22:00",
                        quiet_hours_end="07:00",
                        min_severity="medium",
                        rate_limit_minutes=15
                    )
                    self.user_settings[DEFAULT_USER_ID] = default_settings
                    logger.info("Auto-configured default user from environment variables")
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
    async def save_user_settings(self, settings: NotificationSettings):
        user_settings = UserSettings(
            user_id=settings.user_id,
            enabled_channels=[ch.value for ch in settings.enabled_channels],
            telegram_chat_id=settings.telegram_chat_id,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            min_severity=settings.min_severity.value,
            rate_limit_minutes=settings.rate_limit_minutes
        )
        self.user_settings[settings.user_id] = user_settings
        point = Point("user_settings") \
            .tag("user_id", settings.user_id) \
            .field("enabled_channels", ",".join(user_settings.enabled_channels)) \
            .field("telegram_chat_id", user_settings.telegram_chat_id or "") \
            .field("quiet_hours_start", user_settings.quiet_hours_start) \
            .field("quiet_hours_end", user_settings.quiet_hours_end) \
            .field("min_severity", user_settings.min_severity) \
            .field("rate_limit_minutes", user_settings.rate_limit_minutes)
        self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        logger.info(f"Saved settings for user {settings.user_id}")
    def _is_quiet_hours(self, settings: UserSettings) -> bool:
        from datetime import datetime
        now = datetime.now().time()
        start = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    def _should_rate_limit(self, settings: UserSettings, category: str) -> bool:
        from datetime import datetime
        if category not in settings.last_alert_times:
            return False
        last_alert = settings.last_alert_times[category]
        minutes_since = (datetime.now() - last_alert).total_seconds() / 60
        return minutes_since < settings.rate_limit_minutes
    def _severity_check(self, alert_severity, min_severity: str) -> bool:
        severity_order = ["low", "medium", "high", "critical"]
        alert_idx = severity_order.index(alert_severity.value)
        min_idx = severity_order.index(min_severity)
        return alert_idx >= min_idx
    async def send_alert(self, alert, user_id: str = DEFAULT_USER_ID):
        from datetime import datetime
        if alert.category == AlertCategory.BATTERY_CRITICAL and alert.severity != AlertSeverity.CRITICAL:
            alert = alert.model_copy(update={"severity": AlertSeverity.CRITICAL})
        settings = self.user_settings.get(user_id)
        if not settings:
            logger.warning(f"No settings found for user {user_id}")
            return
        if not self._severity_check(alert.severity, settings.min_severity):
            logger.info(f"Alert {alert.category} below minimum severity threshold")
            return
        if alert.severity != AlertSeverity.CRITICAL and self._is_quiet_hours(settings):
            logger.info(f"Skipping alert {alert.category} during quiet hours")
            return
        if self._should_rate_limit(settings, alert.category.value):
            logger.info(f"Rate limiting alert {alert.category}")
            return
        success = False
        for channel in settings.enabled_channels:
            if channel == NotificationChannel.TELEGRAM.value:
                if await self._send_telegram(alert, settings):
                    success = True
        if success:
            settings.last_alert_times[alert.category.value] = datetime.now()
            point = Point("alerts") \
                .tag("user_id", user_id) \
                .tag("category", alert.category.value) \
                .tag("severity", alert.severity.value) \
                .field("title", alert.title) \
                .field("message", alert.message)
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    async def _send_telegram(self, alert, settings):
        if not self.telegram_bot or not settings.telegram_chat_id:
            logger.warning("Telegram not configured for this user")
            return False
        try:
            emoji = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🔥",
                AlertSeverity.CRITICAL: "🚨"
            }[alert.severity]
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
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
    async def shutdown(self):
        if self.influx_client:
            self.influx_client.close()
