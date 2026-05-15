import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import zuva_api.notification_service as svc_module
from zuva_api.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    NotificationChannel,
    NotificationSettings,
    UserSettings,
)


class FakeWriteApi:
    def __init__(self):
        self.calls = []

    def write(self, bucket, record):
        self.calls.append((bucket, record))


class FakeInfluxClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_initialize_sets_clients_and_bot(monkeypatch):
    fake_client = FakeInfluxClient()
    write_api = FakeWriteApi()

    monkeypatch.setattr(svc_module, "get_influx_client", lambda: fake_client)
    monkeypatch.setattr(svc_module, "get_write_api", lambda _: write_api)
    monkeypatch.setattr(svc_module, "get_query_api", lambda _: SimpleNamespace(query=lambda query: []))
    monkeypatch.setattr(svc_module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(svc_module, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(svc_module, "DEFAULT_USER_ID", "userx")
    monkeypatch.setattr(svc_module, "Bot", lambda token: SimpleNamespace(token=token))

    service = svc_module.NotificationService()
    await service.initialize()

    assert service.influx_client is fake_client
    assert service.write_api is write_api
    assert service.telegram_bot is not None


@pytest.mark.asyncio
async def test_save_user_settings_writes_and_caches(monkeypatch):
    service = svc_module.NotificationService()
    service.write_api = FakeWriteApi()

    settings = NotificationSettings(
        user_id="u1",
        enabled_channels=[NotificationChannel.TELEGRAM],
        telegram_chat_id="chat1",
        min_severity=AlertSeverity.HIGH,
        rate_limit_minutes=10,
    )

    await service.save_user_settings(settings)

    assert "u1" in service.user_settings
    assert service.user_settings["u1"].min_severity == "high"
    assert len(service.write_api.calls) == 1


def test_is_quiet_hours_handles_midnight_window():
    service = svc_module.NotificationService()
    now = datetime.now()
    start = (now - timedelta(minutes=1)).strftime("%H:%M")
    end = (now + timedelta(minutes=1)).strftime("%H:%M")
    settings = UserSettings(
        user_id="u",
        enabled_channels=["telegram"],
        quiet_hours_start=start,
        quiet_hours_end=end,
    )

    assert service._is_quiet_hours(settings) is True


def test_should_rate_limit_true_when_recent():
    service = svc_module.NotificationService()
    settings = UserSettings(user_id="u", enabled_channels=["telegram"], rate_limit_minutes=15)
    settings.last_alert_times["grid_outage"] = datetime.now() - timedelta(minutes=5)

    assert service._should_rate_limit(settings, "grid_outage") is True


def test_severity_check_threshold_logic():
    service = svc_module.NotificationService()

    assert service._severity_check(AlertSeverity.HIGH, "medium") is True
    assert service._severity_check(AlertSeverity.LOW, "high") is False


@pytest.mark.asyncio
async def test_send_alert_critical_battery_forces_critical_and_writes(monkeypatch):
    service = svc_module.NotificationService()
    service.write_api = FakeWriteApi()
    settings = UserSettings(
        user_id="u1",
        enabled_channels=["telegram"],
        telegram_chat_id="chat",
        min_severity="low",
    )
    service.user_settings["u1"] = settings

    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: False)
    monkeypatch.setattr(service, "_should_rate_limit", lambda *_: False)
    service._send_telegram = AsyncMock(return_value=True)

    alert = Alert(
        category=AlertCategory.BATTERY_CRITICAL,
        severity=AlertSeverity.HIGH,
        title="Battery",
        message="Low",
    )

    await service.send_alert(alert, "u1")

    service._send_telegram.assert_awaited_once()
    sent_alert = service._send_telegram.await_args.args[0]
    assert sent_alert.severity == AlertSeverity.CRITICAL
    assert len(service.write_api.calls) == 1


@pytest.mark.asyncio
async def test_send_alert_skips_when_user_missing():
    service = svc_module.NotificationService()
    service._send_telegram = AsyncMock(return_value=True)

    alert = Alert(
        category=AlertCategory.SYSTEM_ERROR,
        severity=AlertSeverity.HIGH,
        title="Err",
        message="msg",
    )

    await service.send_alert(alert, "missing")

    service._send_telegram.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_alert_skips_on_quiet_hours_non_critical(monkeypatch):
    service = svc_module.NotificationService()
    settings = UserSettings(
        user_id="u1",
        enabled_channels=["telegram"],
        telegram_chat_id="chat",
        min_severity="low",
    )
    service.user_settings["u1"] = settings
    service._send_telegram = AsyncMock(return_value=True)

    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: True)
    monkeypatch.setattr(service, "_should_rate_limit", lambda *_: False)

    alert = Alert(
        category=AlertCategory.SYSTEM_ERROR,
        severity=AlertSeverity.MEDIUM,
        title="Err",
        message="msg",
    )

    await service.send_alert(alert, "u1")

    service._send_telegram.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_telegram_returns_false_when_not_configured():
    service = svc_module.NotificationService()
    settings = UserSettings(user_id="u1", enabled_channels=["telegram"], telegram_chat_id=None)

    alert = Alert(
        category=AlertCategory.SYSTEM_ERROR,
        severity=AlertSeverity.MEDIUM,
        title="Title",
        message="Message",
    )

    ok = await service._send_telegram(alert, settings)
    assert ok is False


@pytest.mark.asyncio
async def test_send_telegram_handles_telegram_error():
    service = svc_module.NotificationService()

    class BotWithError:
        async def send_message(self, chat_id, text):
            raise svc_module.TelegramError("bad")

    service.telegram_bot = BotWithError()
    settings = UserSettings(user_id="u1", enabled_channels=["telegram"], telegram_chat_id="chat")

    alert = Alert(
        category=AlertCategory.SYSTEM_ERROR,
        severity=AlertSeverity.MEDIUM,
        title="Title",
        message="Message",
        metadata={"x": 1},
    )

    ok = await service._send_telegram(alert, settings)
    assert ok is False


@pytest.mark.asyncio
async def test_shutdown_closes_client():
    service = svc_module.NotificationService()
    service.influx_client = FakeInfluxClient()

    await service.shutdown()

    assert service.influx_client.closed is True
