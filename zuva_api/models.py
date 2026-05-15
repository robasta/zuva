from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertCategory(str, Enum):
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    GRID_OUTAGE = "grid_outage"
    GRID_RESTORED = "grid_restored"
    HIGH_CONSUMPTION = "high_consumption"
    SYSTEM_ERROR = "system_error"

class NotificationSettings(BaseModel):
    user_id: str
    enabled_channels: List[NotificationChannel]
    telegram_chat_id: Optional[str] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: AlertSeverity = AlertSeverity.MEDIUM
    rate_limit_minutes: int = 15

class Alert(BaseModel):
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
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
