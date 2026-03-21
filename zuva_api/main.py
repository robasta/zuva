"""
Sunsynk Notification Service
Simplified service for sending Telegram notifications
based on solar inverter alerts.
"""
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Telegram Bot
from telegram import Bot
from telegram.error import TelegramError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "sunsynk-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sunsynk")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "solar_data")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    TELEGRAM = "telegram"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    """Alert categories"""
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    GRID_OUTAGE = "grid_outage"
    GRID_RESTORED = "grid_restored"
    HIGH_CONSUMPTION = "high_consumption"
    SYSTEM_ERROR = "system_error"


# Pydantic Models for API
class NotificationSettings(BaseModel):
    """User notification preferences"""
    user_id: str
    enabled_channels: List[NotificationChannel]
    telegram_chat_id: Optional[str] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: AlertSeverity = AlertSeverity.MEDIUM
    rate_limit_minutes: int = 15


class Alert(BaseModel):
    """Alert to be sent"""
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Data storage
@dataclass
class UserSettings:
    """Internal user settings storage"""
    user_id: str
    enabled_channels: List[str]
    telegram_chat_id: Optional[str] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: str = "medium"
    rate_limit_minutes: int = 15
    last_alert_times: Dict[str, datetime] = field(default_factory=dict)


class NotificationService:
    """Handles notification delivery via Telegram"""
    
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.query_api = None
        self.telegram_bot: Optional[Bot] = None
        self.user_settings: Dict[str, UserSettings] = {}
        
    async def initialize(self):
        """Initialize connections and load settings"""
        # InfluxDB
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.influx_client.query_api()
        
        # Telegram Bot
        if TELEGRAM_BOT_TOKEN:
            self.telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logger.info("Telegram bot initialized")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set - Telegram notifications disabled")
        
        # Load user settings from InfluxDB
        await self._load_user_settings()
    
    async def _load_user_settings(self):
        """Load user settings from InfluxDB"""
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
                        # Reconstruct settings from fields
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
            
            # Auto-create default user settings from environment variables if not exists
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
        """Save user settings to InfluxDB and memory"""
        user_settings = UserSettings(
            user_id=settings.user_id,
            enabled_channels=[ch.value for ch in settings.enabled_channels],
            telegram_chat_id=settings.telegram_chat_id,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            min_severity=settings.min_severity.value,
            rate_limit_minutes=settings.rate_limit_minutes
        )
        
        # Save to memory
        self.user_settings[settings.user_id] = user_settings
        
        # Save to InfluxDB
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
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        start = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:  # Crosses midnight
            return now >= start or now <= end
    
    def _should_rate_limit(self, settings: UserSettings, category: str) -> bool:
        """Check if alert should be rate limited"""
        if category not in settings.last_alert_times:
            return False
        
        last_alert = settings.last_alert_times[category]
        minutes_since = (datetime.now() - last_alert).total_seconds() / 60
        
        return minutes_since < settings.rate_limit_minutes
    
    def _severity_check(self, alert_severity: AlertSeverity, min_severity: str) -> bool:
        """Check if alert severity meets minimum threshold"""
        severity_order = ["low", "medium", "high", "critical"]
        alert_idx = severity_order.index(alert_severity.value)
        min_idx = severity_order.index(min_severity)
        return alert_idx >= min_idx
    
    async def send_alert(self, alert: Alert, user_id: str = DEFAULT_USER_ID):
        """Send alert to user via configured channels"""
        if alert.category == AlertCategory.BATTERY_CRITICAL and alert.severity != AlertSeverity.CRITICAL:
            alert = alert.model_copy(update={"severity": AlertSeverity.CRITICAL})

        settings = self.user_settings.get(user_id)
        if not settings:
            logger.warning(f"No settings found for user {user_id}")
            return
        
        # Check severity threshold
        if not self._severity_check(alert.severity, settings.min_severity):
            logger.info(f"Alert {alert.category} below minimum severity threshold")
            return
        
        # Check quiet hours (except for critical alerts)
        if alert.severity != AlertSeverity.CRITICAL and self._is_quiet_hours(settings):
            logger.info(f"Skipping alert {alert.category} during quiet hours")
            return
        
        # Check rate limiting
        if self._should_rate_limit(settings, alert.category.value):
            logger.info(f"Rate limiting alert {alert.category}")
            return
        
        # Send to enabled channels
        success = False
        for channel in settings.enabled_channels:
            if channel == NotificationChannel.TELEGRAM.value:
                if await self._send_telegram(alert, settings):
                    success = True
        
        # Update last alert time
        if success:
            settings.last_alert_times[alert.category.value] = datetime.now()
            
            # Log alert to InfluxDB
            point = Point("alerts") \
                .tag("user_id", user_id) \
                .tag("category", alert.category.value) \
                .tag("severity", alert.severity.value) \
                .field("title", alert.title) \
                .field("message", alert.message)
            
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    
    async def _send_telegram(self, alert: Alert, settings: UserSettings) -> bool:
        """Send alert via Telegram"""
        if not self.telegram_bot or not settings.telegram_chat_id:
            logger.warning("Telegram not configured for this user")
            return False
        
        try:
            # Format message with emoji based on severity
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
        """Cleanup resources"""
        if self.influx_client:
            self.influx_client.close()


# FastAPI app
app = FastAPI(title="Sunsynk Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notification_service = NotificationService()


@app.on_event("startup")
async def startup():
    await notification_service.initialize()


@app.on_event("shutdown")
async def shutdown():
    await notification_service.shutdown()


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "telegram_enabled": notification_service.telegram_bot is not None,
        "users_configured": len(notification_service.user_settings)
    }


@app.post("/settings")
async def update_settings(settings: NotificationSettings):
    """Update notification settings for a user"""
    await notification_service.save_user_settings(settings)
    return {"status": "success", "user_id": settings.user_id}


@app.get("/settings/{user_id}")
async def get_settings(user_id: str):
    """Get notification settings for a user"""
    settings = notification_service.user_settings.get(user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    
    return asdict(settings)


@app.post("/alert")
async def send_alert(alert: Alert, user_id: str = "default"):
    """Send an alert to a user"""
    await notification_service.send_alert(alert, user_id)
    return {"status": "sent"}


@app.get("/alerts/history/{user_id}")
async def get_alert_history(user_id: str, hours: int = 24):
    """Get alert history for a user"""
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "alerts")
            |> filter(fn: (r) => r.user_id == "{user_id}")
    '''
    
    try:
        result = notification_service.query_api.query(query=query)
        alerts = []
        for table in result:
            for record in table.records:
                alerts.append({
                    "time": record.get_time(),
                    "category": record.values.get("category"),
                    "severity": record.values.get("severity"),
                    "title": record.values.get("title"),
                    "message": record.values.get("message")
                })
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    api_port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=api_port)
