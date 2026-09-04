from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import zuva_api.notification_service as svc_module
from zuva_api.history_store import HistoryStore
from zuva_api.models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    NotificationChannel,
    NotificationSettings,
    UserSettings,
)
from zuva_api.settings_store import SettingsStore
from zuva_api.timeutil import local_now


@pytest.fixture(autouse=True)
def db_in_tmp_path(tmp_path, monkeypatch):
    """Any default-constructed store must land in tmp_path, never in /data."""
    monkeypatch.setenv("SETTINGS_DB_PATH", str(tmp_path / "zuva.db"))


@pytest.fixture
def store(tmp_path):
    """A real SQLite store on a temp path - never the container's /data volume."""
    store = SettingsStore(str(tmp_path / "zuva.db"))
    store.initialize()
    return store


@pytest.fixture
def history(tmp_path):
    history = HistoryStore(str(tmp_path / "zuva.db"))
    history.initialize()
    return history


@pytest.fixture
def service(store, history):
    return svc_module.NotificationService(settings_store=store, history_store=history)


def make_settings(**overrides):
    values = {
        "user_id": "u1",
        "enabled_channels": ["telegram"],
        "telegram_chat_id": "chat",
        "min_severity": "low",
    }
    values.update(overrides)
    return UserSettings(**values)


def make_alert(**overrides):
    values = {
        "category": AlertCategory.SYSTEM_ERROR,
        "severity": AlertSeverity.HIGH,
        "title": "Title",
        "message": "Message",
    }
    values.update(overrides)
    return Alert(**values)


@pytest.mark.asyncio
async def test_initialize_prepares_storage_and_bot(monkeypatch, store, history):
    monkeypatch.setattr(svc_module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(svc_module, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(svc_module, "DEFAULT_USER_ID", "userx")
    monkeypatch.setattr(svc_module, "Bot", lambda token: SimpleNamespace(token=token))

    service = svc_module.NotificationService(settings_store=store, history_store=history)
    await service.initialize()

    assert service.telegram_bot is not None
    # A default user is derived from the environment so alerts are not dropped.
    assert "userx" in service.user_settings


@pytest.mark.asyncio
async def test_initialize_survives_an_unusable_history_store(monkeypatch, store):
    """History is a record, not the job: alerts must still go out without it."""
    monkeypatch.setattr(svc_module, "TELEGRAM_BOT_TOKEN", None)
    unusable = HistoryStore("/proc/zuva-cannot-write-here/zuva.db")

    service = svc_module.NotificationService(settings_store=store, history_store=unusable)
    await service.initialize()

    assert service.user_settings == {}


@pytest.mark.asyncio
async def test_settings_are_persisted_not_stored_as_history(service, store, history):
    settings = NotificationSettings(
        user_id="u1",
        enabled_channels=[NotificationChannel.TELEGRAM],
        telegram_chat_id="chat1",
        min_severity=AlertSeverity.HIGH,
        rate_limit_minutes=10,
    )

    await service.save_user_settings(settings)

    assert service.user_settings["u1"].min_severity == "high"
    # Configuration belongs in the settings store; a time-series write with a
    # bounded read range is what used to lose it on restart.
    assert history.recent_alerts("u1", hours=1) == []
    assert store.load_all()["u1"].telegram_chat_id == "chat1"


@pytest.mark.asyncio
async def test_settings_survive_a_restart(service, store, monkeypatch):
    monkeypatch.setattr(svc_module, "TELEGRAM_BOT_TOKEN", None)
    await service.save_user_settings(
        NotificationSettings(
            user_id="u1",
            enabled_channels=[NotificationChannel.TELEGRAM],
            telegram_chat_id="chat1",
            min_severity=AlertSeverity.HIGH,
            rate_limit_minutes=10,
        )
    )

    restarted = svc_module.NotificationService(settings_store=store)
    await restarted._load_user_settings()

    assert restarted.user_settings["u1"].telegram_chat_id == "chat1"
    assert restarted.user_settings["u1"].rate_limit_minutes == 10


def test_is_quiet_hours_handles_midnight_window(service):
    now = local_now()
    settings = make_settings(
        quiet_hours_start=(now - timedelta(minutes=1)).strftime("%H:%M"),
        quiet_hours_end=(now + timedelta(minutes=1)).strftime("%H:%M"),
    )

    assert service._is_quiet_hours(settings) is True


def test_is_quiet_hours_uses_the_configured_timezone(service, monkeypatch):
    monkeypatch.setattr(
        svc_module, "local_now", lambda: local_now().replace(hour=23, minute=0)
    )
    settings = make_settings(quiet_hours_start="22:00", quiet_hours_end="07:00")

    assert service._is_quiet_hours(settings) is True

    monkeypatch.setattr(
        svc_module, "local_now", lambda: local_now().replace(hour=12, minute=0)
    )
    assert service._is_quiet_hours(settings) is False


def test_is_quiet_hours_treats_malformed_config_as_disabled(service):
    assert service._is_quiet_hours(make_settings(quiet_hours_start="not-a-time")) is False


def test_should_rate_limit_true_when_recent(service):
    settings = make_settings(rate_limit_minutes=15)
    settings.last_alert_times["grid_outage"] = local_now() - timedelta(minutes=5)

    assert service._should_rate_limit(settings, "grid_outage") is True


def test_should_rate_limit_accepts_naive_stored_timestamps(service):
    """Timestamps loaded from disk may be naive; comparing them must not raise.

    A naive stamp is read as wall-clock time in TIMEZONE, so it has to be built
    from local_now(), not datetime.now() - otherwise the test only passes on a
    machine whose system timezone happens to match TIMEZONE.
    """
    settings = make_settings(rate_limit_minutes=15)
    settings.last_alert_times["grid_outage"] = local_now().replace(tzinfo=None)

    assert service._should_rate_limit(settings, "grid_outage") is True


def test_should_rate_limit_false_when_stale(service):
    settings = make_settings(rate_limit_minutes=15)
    settings.last_alert_times["grid_outage"] = local_now() - timedelta(hours=2)

    assert service._should_rate_limit(settings, "grid_outage") is False


def test_severity_check_threshold_logic(service):
    assert service._severity_check(AlertSeverity.HIGH, "medium") is True
    assert service._severity_check(AlertSeverity.LOW, "high") is False


def test_severity_check_tolerates_unknown_values(service):
    assert service._severity_check("catastrophic", "medium") is True
    assert service._severity_check(AlertSeverity.HIGH, "nonsense") is True
    assert service._severity_check(AlertSeverity.LOW, "nonsense") is False


@pytest.mark.asyncio
async def test_send_alert_critical_battery_forces_critical_and_writes(service, history, monkeypatch):
    service.user_settings["u1"] = make_settings()
    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: False)
    monkeypatch.setattr(service, "_should_rate_limit", lambda *_: False)
    service._send_telegram = AsyncMock(return_value=True)

    result = await service.send_alert(
        make_alert(category=AlertCategory.BATTERY_CRITICAL, severity=AlertSeverity.HIGH), "u1"
    )

    assert result["status"] == "sent"
    sent_alert = service._send_telegram.await_args.args[0]
    assert sent_alert.severity == AlertSeverity.CRITICAL
    # The delivered severity is what the history records, not the requested one.
    stored = history.recent_alerts("u1", hours=1)
    assert len(stored) == 1
    assert stored[0]["severity"] == "critical"
    assert stored[0]["category"] == "battery_critical"


@pytest.mark.asyncio
async def test_send_alert_unknown_user_is_reported(service):
    service._send_telegram = AsyncMock(return_value=True)

    result = await service.send_alert(make_alert(), "missing")

    assert result["status"] == "unknown_user"
    assert "missing" in result["reason"]
    service._send_telegram.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_alert_skips_on_quiet_hours_non_critical(service, monkeypatch):
    service.user_settings["u1"] = make_settings()
    service._send_telegram = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: True)
    monkeypatch.setattr(service, "_should_rate_limit", lambda *_: False)

    result = await service.send_alert(make_alert(severity=AlertSeverity.MEDIUM), "u1")

    assert result == {"status": "suppressed", "reason": "quiet_hours"}
    service._send_telegram.assert_not_awaited()


@pytest.mark.asyncio
async def test_critical_alerts_ignore_quiet_hours(service, monkeypatch):
    service.user_settings["u1"] = make_settings()
    service._send_telegram = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: True)

    result = await service.send_alert(make_alert(severity=AlertSeverity.CRITICAL), "u1")

    assert result["status"] == "sent"


@pytest.mark.asyncio
async def test_send_alert_below_min_severity_is_suppressed(service):
    service.user_settings["u1"] = make_settings(min_severity="critical")
    service._send_telegram = AsyncMock(return_value=True)

    result = await service.send_alert(make_alert(severity=AlertSeverity.LOW), "u1")

    assert result == {"status": "suppressed", "reason": "below_min_severity"}


@pytest.mark.asyncio
async def test_send_alert_without_channels_fails_loudly(service):
    service.user_settings["u1"] = make_settings(enabled_channels=[])

    result = await service.send_alert(make_alert(), "u1")

    assert result == {"status": "failed", "reason": "no_enabled_channels"}


@pytest.mark.asyncio
async def test_failed_delivery_does_not_consume_the_rate_limit_window(service, history, monkeypatch):
    """A Telegram outage must not silence the next real alert."""
    settings = make_settings()
    service.user_settings["u1"] = settings
    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: False)
    service._send_telegram = AsyncMock(return_value=False)

    result = await service.send_alert(make_alert(), "u1")

    assert result == {"status": "failed", "reason": "all_channels_failed"}
    assert settings.last_alert_times == {}
    # Nothing was delivered, so nothing is recorded as sent.
    assert history.recent_alerts("u1", hours=1) == []


@pytest.mark.asyncio
async def test_rate_limit_state_is_persisted(service, store, monkeypatch):
    service.user_settings["u1"] = make_settings()
    monkeypatch.setattr(service, "_is_quiet_hours", lambda _: False)
    service._send_telegram = AsyncMock(return_value=True)
    store.save(make_settings())

    await service.send_alert(make_alert(category=AlertCategory.GRID_OUTAGE), "u1")

    # A restart must not re-arm every category and flood the user.
    reloaded = store.load_all()["u1"]
    assert "grid_outage" in reloaded.last_alert_times
    assert svc_module.NotificationService(settings_store=store)._should_rate_limit(
        reloaded, "grid_outage"
    ) is True


@pytest.mark.asyncio
async def test_send_telegram_returns_false_when_not_configured(service):
    ok = await service._send_telegram(make_alert(), make_settings(telegram_chat_id=None))
    assert ok is False


@pytest.mark.asyncio
async def test_send_telegram_handles_telegram_error(service):
    class BotWithError:
        async def send_message(self, chat_id, text):
            raise svc_module.TelegramError("bad")

    service.telegram_bot = BotWithError()

    ok = await service._send_telegram(make_alert(metadata={"x": 1}), make_settings())

    assert ok is False


@pytest.mark.asyncio
async def test_send_telegram_formats_metadata(service):
    sent = {}

    class Bot:
        async def send_message(self, chat_id, text):
            sent["chat_id"] = chat_id
            sent["text"] = text
            return SimpleNamespace(message_id=7)

    service.telegram_bot = Bot()

    ok = await service._send_telegram(make_alert(metadata={"battery_soc": 9}), make_settings())

    assert ok is True
    assert sent["chat_id"] == "chat"
    assert "battery_soc: 9" in sent["text"]
