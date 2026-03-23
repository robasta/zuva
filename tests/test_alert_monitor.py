from unittest.mock import AsyncMock

import pytest

from zuva.collector import alert_monitor as monitor_module


@pytest.mark.asyncio
async def test_connect_client_with_retry_succeeds_on_second_attempt(monkeypatch):
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            if len(instances) == 1:
                raise monitor_module.LoginRateLimitedException("rate limited")

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(monitor_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(monitor_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(monitor_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(monitor_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(monitor_module.asyncio, "sleep", sleep_mock)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()

    client = await monitor.connect_client_with_retry()

    assert client is instances[1]
    assert instances[0].closed is True
    assert instances[1].closed is False
    sleep_mock.assert_awaited_once_with(900)
    monitor.send_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_connect_client_with_retry_sends_critical_alert_after_second_failure(monkeypatch):
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            raise monitor_module.InvalidCredentialsException()

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(monitor_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(monitor_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(monitor_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(monitor_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(monitor_module.asyncio, "sleep", sleep_mock)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()

    client = await monitor.connect_client_with_retry()

    assert client is None
    assert all(client_instance.closed for client_instance in instances)
    sleep_mock.assert_awaited_once_with(900)
    monitor.send_alert.assert_awaited_once()

    _, kwargs = monitor.send_alert.await_args
    assert kwargs["category"] == "sunsynk_login_failure"
    assert kwargs["severity"] == "critical"
    assert kwargs["metadata"]["attempts"] == 2
    assert kwargs["metadata"]["retry_wait_seconds"] == 900


@pytest.mark.asyncio
async def test_connect_client_with_retry_connectivity_failure_uses_connectivity_alert_title(monkeypatch):
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            raise monitor_module.SunsynkConnectionError("internet down")

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(monitor_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(monitor_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(monitor_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(monitor_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(monitor_module.asyncio, "sleep", sleep_mock)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()

    client = await monitor.connect_client_with_retry()

    assert client is None
    assert all(client_instance.closed for client_instance in instances)
    sleep_mock.assert_awaited_once_with(900)
    monitor.send_alert.assert_awaited_once()

    _, kwargs = monitor.send_alert.await_args
    assert kwargs["title"] == "🚨 Sunsynk Connectivity Failed Twice"


@pytest.mark.asyncio
async def test_grid_alert_no_alert_on_single_outage_reading():
    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    await monitor.check_grid_alerts(0.0, 0.0, 0)

    monitor.send_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_grid_alert_fires_after_consecutive_outage_readings(monkeypatch):
    monkeypatch.setattr(monitor_module, "GRID_OUTAGE_CONSECUTIVE_READINGS", 3)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    for _ in range(3):
        await monitor.check_grid_alerts(0.0, 0.0, 0)

    monitor.send_alert.assert_awaited_once()
    _, kwargs = monitor.send_alert.await_args
    assert kwargs["category"] == "grid_outage"


@pytest.mark.asyncio
async def test_grid_alert_counter_resets_on_intermittent_recovery(monkeypatch):
    monkeypatch.setattr(monitor_module, "GRID_OUTAGE_CONSECUTIVE_READINGS", 3)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    await monitor.check_grid_alerts(0.0, 0.0, 0)
    await monitor.check_grid_alerts(0.0, 0.0, 0)
    await monitor.check_grid_alerts(5.0, 230.0, 1)
    await monitor.check_grid_alerts(0.0, 0.0, 0)

    monitor.send_alert.assert_not_awaited()
    assert monitor.grid_outage_consecutive_count == 1


@pytest.mark.asyncio
async def test_grid_alert_no_false_positive_when_power_low_but_voltage_normal():
    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    for _ in range(5):
        await monitor.check_grid_alerts(0.05, 230.0, 1)

    monitor.send_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_grid_alert_ambiguous_when_voltage_is_none():
    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True
    monitor.grid_outage_consecutive_count = 2
    monitor.grid_restore_consecutive_count = 1

    await monitor.check_grid_alerts(0.0, None, 0)
    await monitor.check_grid_alerts(0.0, None, 0)
    await monitor.check_grid_alerts(0.0, None, 0)

    monitor.send_alert.assert_not_awaited()
    assert monitor.grid_outage_consecutive_count == 2
    assert monitor.grid_restore_consecutive_count == 1
    assert monitor.last_grid_status is True


@pytest.mark.asyncio
async def test_grid_alert_cooldown_prevents_repeat_alerts(monkeypatch):
    monkeypatch.setattr(monitor_module, "GRID_OUTAGE_CONSECUTIVE_READINGS", 1)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    await monitor.check_grid_alerts(0.0, 0.0, 0)
    assert monitor.send_alert.await_count == 1

    monitor.last_grid_status = True
    monitor.grid_outage_consecutive_count = 0
    monitor.grid_restore_consecutive_count = 0

    await monitor.check_grid_alerts(0.0, 0.0, 0)

    assert monitor.send_alert.await_count == 1


@pytest.mark.asyncio
async def test_grid_restore_alert_fires_after_consecutive_active_readings(monkeypatch):
    monkeypatch.setattr(monitor_module, "GRID_OUTAGE_CONSECUTIVE_READINGS", 3)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = False

    for _ in range(3):
        await monitor.check_grid_alerts(5.0, 230.0, 1)

    monitor.send_alert.assert_awaited_once()
    _, kwargs = monitor.send_alert.await_args
    assert kwargs["category"] == "grid_restored"


@pytest.mark.asyncio
async def test_grid_alert_metadata_includes_voltage_and_status(monkeypatch):
    monkeypatch.setattr(monitor_module, "GRID_OUTAGE_CONSECUTIVE_READINGS", 1)

    monitor = monitor_module.AlertMonitor()
    monitor.send_alert = AsyncMock()
    monitor.last_grid_status = True

    await monitor.check_grid_alerts(0.0, 0.0, 0)

    monitor.send_alert.assert_awaited_once()
    _, kwargs = monitor.send_alert.await_args
    metadata = kwargs["metadata"]
    assert "grid_voltage" in metadata
    assert "grid_status" in metadata
    assert "consecutive_readings" in metadata
