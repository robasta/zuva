"""Tests for AlertManager alert fetching behaviour."""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Ensure backend package imports resolve when tests execute from repo root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.main import Alert, AlertManager, AlertSeverity, AlertStatus, NotificationChannel


@pytest_asyncio.fixture
async def alert_manager():
    """Provide an AlertManager with database interactions mocked out."""
    manager = AlertManager()
    mock_db = MagicMock()
    mock_db.get_alerts = AsyncMock(return_value=[])
    mock_db.get_active_alerts = AsyncMock(return_value=[])
    mock_db.write_alert = AsyncMock(return_value=True)
    mock_db.update_alert_status = AsyncMock(return_value=True)

    manager.db_manager = mock_db
    manager.AlertData = MagicMock()
    manager.save_alert_to_db = AsyncMock(return_value=True)
    yield manager


@pytest.mark.asyncio
async def test_get_recent_alerts_falls_back_to_memory(alert_manager):
    """When the database returns no rows the in-memory alerts should be used."""
    alert = Alert(
        id="test-id",
        title="Test",
        message="Test message",
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACTIVE,
        category="test",
        timestamp=datetime.now() - timedelta(minutes=1),
        metadata={}
    )
    alert_manager.alert_history.append(alert)

    results = await alert_manager.get_recent_alerts(hours=1)

    assert len(results) == 1
    assert results[0]["id"] == "test-id"
    assert results[0]["status"] == "active"


@pytest.mark.asyncio
async def test_get_recent_alerts_prefers_database(alert_manager):
    """Database results should be returned when available."""
    db_alert = {
        "id": "db-id",
        "title": "DB",
        "message": "From database",
        "severity": "low",
        "status": "active",
        "category": "test",
        "timestamp": datetime.now().isoformat(),
        "metadata": {}
    }
    alert_manager.db_manager.get_alerts.return_value = [db_alert]

    # Populate history with a stale entry that should be ignored
    old_alert = Alert(
        id="memory-id",
        title="Memory",
        message="In memory",
        severity=AlertSeverity.LOW,
        status=AlertStatus.RESOLVED,
        category="test",
        timestamp=datetime.now() - timedelta(hours=2),
        metadata={}
    )
    alert_manager.alert_history.append(old_alert)

    results = await alert_manager.get_recent_alerts(hours=1)

    assert results == [db_alert]


@pytest.mark.asyncio
async def test_get_recent_alerts_deduplicates_memory(alert_manager):
    """Active alerts should overwrite historical duplicates when falling back."""
    base_time = datetime.now() - timedelta(minutes=5)

    history_alert = Alert(
        id="dup-id",
        title="History",
        message="Old message",
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.RESOLVED,
        category="test",
        timestamp=base_time,
        metadata={"source": "history"}
    )
    alert_manager.alert_history.append(history_alert)

    active_alert = Alert(
        id="dup-id",
        title="Active",
        message="New message",
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.ACTIVE,
        category="test",
        timestamp=base_time + timedelta(minutes=4),
        metadata={"source": "active"}
    )
    alert_manager.active_alerts[active_alert.id] = active_alert

    alert_manager.db_manager.get_alerts.return_value = []

    results = await alert_manager.get_recent_alerts(hours=1)

    assert len(results) == 1
    alert_payload = results[0]
    assert alert_payload["id"] == "dup-id"
    assert alert_payload["status"] == "active"
    assert alert_payload["metadata"]["source"] == "active"


@pytest.mark.asyncio
async def test_notifications_suppressed_during_cooldown(alert_manager):
    """Alerts should be recorded but not sent while cooldown is active."""
    category = "battery_low"
    now = datetime.now()
    alert = Alert(
        id="cooldown-id",
        title="Battery low",
        message="Low battery",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        category=category,
        timestamp=now,
        metadata={}
    )
    previous_send = now - timedelta(minutes=5)
    alert_manager.last_notification_times[category] = previous_send
    alert_manager.category_cooldowns[category] = timedelta(minutes=30)
    alert_manager.notification_preferences.enabled_channels = [NotificationChannel.PUSH]

    with patch.object(alert_manager, "_send_to_channel", new_callable=AsyncMock) as send_mock:
        await alert_manager._send_notifications(alert)

    send_mock.assert_not_called()
    assert alert.metadata.get("suppressed_reason") == "cooldown"
    assert "suppressed_until" in alert.metadata
    assert alert_manager.last_notification_times[category] == previous_send


@pytest.mark.asyncio
async def test_notifications_resume_after_cooldown(alert_manager):
    """Notifications should be sent once the cooldown window expires."""
    category = "battery_low"
    alert = Alert(
        id="send-id",
        title="Battery low",
        message="Low battery",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        category=category,
        timestamp=datetime.now(),
        metadata={}
    )
    previous_send = datetime.now() - timedelta(minutes=45)
    alert_manager.last_notification_times[category] = previous_send
    alert_manager.category_cooldowns[category] = timedelta(minutes=30)
    alert_manager.notification_preferences.enabled_channels = [NotificationChannel.PUSH]

    with patch.object(alert_manager, "_send_to_channel", new_callable=AsyncMock) as send_mock:
        await alert_manager._send_notifications(alert)

    send_mock.assert_awaited()
    assert "suppressed_reason" not in alert.metadata
    assert alert_manager.last_notification_times[category] >= alert.timestamp