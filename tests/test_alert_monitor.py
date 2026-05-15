import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import zuva.collector.orchestrator as orchestrator_module
from sunsynk.client import LoginRateLimitedException, InvalidCredentialsException, SunsynkConnectionError


class FakeInfluxClient:
    def __init__(self, *args, **kwargs):
        self.closed = False

    def write_api(self, write_options=None):
        return object()

    def query_api(self):
        return object()

    def close(self):
        self.closed = True


def make_orchestrator(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "InfluxDBClient", FakeInfluxClient)
    return orchestrator_module.AlertOrchestrator()


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
                raise LoginRateLimitedException("rate limited")

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", sleep_mock)

    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.notification.send = AsyncMock()

    client = await orchestrator.connect_client_with_retry()

    assert client is instances[1]
    assert instances[0].closed is True
    assert instances[1].closed is False
    sleep_mock.assert_awaited_once_with(900)
    orchestrator.notification.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_connect_client_with_retry_sends_alert_after_second_login_failure(monkeypatch):
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            raise InvalidCredentialsException()

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", sleep_mock)

    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.notification.send = AsyncMock()

    client = await orchestrator.connect_client_with_retry()

    assert client is None
    assert all(client_instance.closed for client_instance in instances)
    sleep_mock.assert_awaited_once_with(900)
    orchestrator.notification.send.assert_awaited_once()

    _, kwargs = orchestrator.notification.send.await_args
    assert kwargs["category"] == "sunsynk_login_failure"
    assert kwargs["severity"] == "critical"
    assert kwargs["metadata"]["attempts"] == 2
    assert kwargs["metadata"]["retry_wait_seconds"] == 900


@pytest.mark.asyncio
async def test_connect_client_with_retry_connectivity_failure_uses_connectivity_title(monkeypatch):
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            raise SunsynkConnectionError("internet down")

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", sleep_mock)

    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.notification.send = AsyncMock()

    client = await orchestrator.connect_client_with_retry()

    assert client is None
    assert all(client_instance.closed for client_instance in instances)
    sleep_mock.assert_awaited_once_with(900)
    orchestrator.notification.send.assert_awaited_once()

    _, kwargs = orchestrator.notification.send.await_args
    assert kwargs["title"] == "🚨 Sunsynk Connectivity Failed Twice"


@pytest.mark.asyncio
async def test_monitor_loop_returns_when_credentials_missing(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", None)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", None)

    orchestrator = make_orchestrator(monkeypatch)

    await orchestrator.monitor_loop()


def test_shutdown_closes_influx_client(monkeypatch):
    orchestrator = make_orchestrator(monkeypatch)

    orchestrator.shutdown()

    assert orchestrator.influx_client.closed is True


@pytest.mark.asyncio
async def test_monitor_loop_writes_telemetry_and_alerts_once(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "POLL_INTERVAL", 1)

    orchestrator = make_orchestrator(monkeypatch)

    fake_client = AsyncMock()
    fake_client.get_plants.return_value = [SimpleNamespace(id=10)]
    fake_client.get_inverters.return_value = [SimpleNamespace(sn="SN-1")]
    fake_client.get_inverter_realtime_battery.return_value = SimpleNamespace(soc=45, power=1.2, get_voltage=lambda: 52.0)
    fake_client.get_inverter_realtime_grid.return_value = SimpleNamespace(get_power=lambda: 0.0, get_voltage=lambda: 40.0, status=0)
    fake_client.get_inverter_realtime_output.return_value = SimpleNamespace(pac=3.1)
    fake_client.get_inverter_realtime_input.return_value = SimpleNamespace(get_power=lambda: 2.7)

    orchestrator.connect_client_with_retry = AsyncMock(return_value=fake_client)
    orchestrator.telemetry.write = AsyncMock()
    orchestrator.alerter.check_battery_alerts = AsyncMock()
    orchestrator.alerter.check_grid_alerts = AsyncMock()
    orchestrator.alerter.check_consumption_alerts = AsyncMock()

    sleep_calls = {"n": 0}

    async def stop_after_first_cycle(_):
        sleep_calls["n"] += 1
        raise asyncio.CancelledError()

    import asyncio
    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", stop_after_first_cycle)

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.monitor_loop()

    orchestrator.telemetry.write.assert_awaited_once()
    orchestrator.alerter.check_battery_alerts.assert_awaited_once()
    orchestrator.alerter.check_grid_alerts.assert_awaited_once()
    orchestrator.alerter.check_consumption_alerts.assert_awaited_once()
    fake_client.close.assert_awaited_once()
