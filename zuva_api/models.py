import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Identifiers end up as InfluxDB tags and query values; keep them boring.
USER_ID_PATTERN = r"^[A-Za-z0-9_.@-]{1,64}$"
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_ORDER = [
    AlertSeverity.LOW.value,
    AlertSeverity.MEDIUM.value,
    AlertSeverity.HIGH.value,
    AlertSeverity.CRITICAL.value,
]


class AlertCategory(str, Enum):
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    GRID_OUTAGE = "grid_outage"
    GRID_RESTORED = "grid_restored"
    HIGH_CONSUMPTION = "high_consumption"
    SYSTEM_ERROR = "system_error"
    # Raised by the collector when it cannot log in to or reach the Sunsynk API.
    # Without this the "monitoring is broken" alert is rejected as invalid.
    SUNSYNK_LOGIN_FAILURE = "sunsynk_login_failure"


def _validate_hhmm(value: str) -> str:
    if not TIME_PATTERN.match(value):
        raise ValueError("must be a 24-hour time of the form HH:MM")
    return value


class NotificationSettings(BaseModel):
    user_id: str = Field(pattern=USER_ID_PATTERN)
    enabled_channels: List[NotificationChannel]
    telegram_chat_id: Optional[str] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: AlertSeverity = AlertSeverity.MEDIUM
    rate_limit_minutes: int = Field(default=15, ge=0, le=1440)

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def check_time_format(cls, value: str) -> str:
        return _validate_hhmm(value)


class Alert(BaseModel):
    category: AlertCategory
    severity: AlertSeverity
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class UserSettings:
    user_id: str
    enabled_channels: List[str]
    telegram_chat_id: Optional[str] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: str = "medium"
    rate_limit_minutes: int = 15
    last_alert_times: Dict[str, Any] = field(default_factory=dict)
