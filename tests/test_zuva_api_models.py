import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zuva_api.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    NotificationChannel,
    NotificationSettings,
    UserSettings,
)


def test_notification_settings_defaults():
    settings = NotificationSettings(user_id="u1", enabled_channels=[NotificationChannel.TELEGRAM])
    assert settings.quiet_hours_start == "22:00"
    assert settings.quiet_hours_end == "07:00"
    assert settings.min_severity == AlertSeverity.MEDIUM
    assert settings.rate_limit_minutes == 15


def test_alert_defaults_metadata_empty_dict():
    alert = Alert(
        category=AlertCategory.SYSTEM_ERROR,
        severity=AlertSeverity.HIGH,
        title="Oops",
        message="Something happened",
    )
    assert alert.metadata == {}


def test_user_settings_default_last_alert_times_isolated():
    a = UserSettings(user_id="u1", enabled_channels=["telegram"])
    b = UserSettings(user_id="u2", enabled_channels=["telegram"])

    a.last_alert_times["x"] = "y"

    assert b.last_alert_times == {}
