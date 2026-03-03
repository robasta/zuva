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
