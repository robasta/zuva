import pytest
from pydantic import ValidationError

from zuva_api.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    NotificationChannel,
    NotificationSettings,
    SEVERITY_ORDER,
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


def test_collector_login_failure_is_a_known_category():
    """The collector's "monitoring is broken" alert must be representable."""
    assert AlertCategory("sunsynk_login_failure") is AlertCategory.SUNSYNK_LOGIN_FAILURE


def test_severity_order_is_ascending():
    assert SEVERITY_ORDER == ["low", "medium", "high", "critical"]


@pytest.mark.parametrize("user_id", ["u1", "user.name", "user@example.com", "a-b_c", "a" * 64])
def test_accepted_user_ids(user_id):
    assert NotificationSettings(user_id=user_id, enabled_channels=[]).user_id == user_id


@pytest.mark.parametrize(
    "user_id", ["", "has space", "../etc/passwd", 'quote"', "a" * 65, "semi;colon"]
)
def test_rejected_user_ids(user_id):
    # User ids end up in stored rows and URL path segments; keep them boring.
    with pytest.raises(ValidationError):
        NotificationSettings(user_id=user_id, enabled_channels=[])


@pytest.mark.parametrize("value", ["00:00", "07:30", "23:59"])
def test_accepted_quiet_hours(value):
    settings = NotificationSettings(
        user_id="u1", enabled_channels=[], quiet_hours_start=value, quiet_hours_end=value
    )
    assert settings.quiet_hours_start == value


@pytest.mark.parametrize("value", ["24:00", "7:30", "23:60", "not-a-time", "22:00:00", ""])
def test_rejected_quiet_hours(value):
    # A malformed window used to disable quiet hours silently at send time.
    with pytest.raises(ValidationError):
        NotificationSettings(user_id="u1", enabled_channels=[], quiet_hours_start=value)


@pytest.mark.parametrize("value", [-1, 1441])
def test_rate_limit_minutes_is_bounded(value):
    with pytest.raises(ValidationError):
        NotificationSettings(user_id="u1", enabled_channels=[], rate_limit_minutes=value)


def test_rate_limit_minutes_allows_disabling(value=0):
    assert NotificationSettings(
        user_id="u1", enabled_channels=[], rate_limit_minutes=value
    ).rate_limit_minutes == 0


@pytest.mark.parametrize("field", ["title", "message"])
def test_alert_text_cannot_be_empty(field):
    values = {
        "category": AlertCategory.SYSTEM_ERROR,
        "severity": AlertSeverity.HIGH,
        "title": "Oops",
        "message": "Something happened",
        field: "",
    }
    with pytest.raises(ValidationError):
        Alert(**values)


def test_alert_message_length_is_capped():
    with pytest.raises(ValidationError):
        Alert(
            category=AlertCategory.SYSTEM_ERROR,
            severity=AlertSeverity.HIGH,
            title="Oops",
            message="x" * 2001,
        )


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        Alert(
            category="not_a_category",
            severity=AlertSeverity.HIGH,
            title="Oops",
            message="msg",
        )
