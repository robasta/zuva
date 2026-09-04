import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import zuva.collector.orchestrator as orchestrator_module
from sunsynk.client import (
    InvalidCredentialsException,
    LoginRateLimitedException,
    SunsynkConnectionError,
    VerificationCodeRequiredException,
)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Keep the collector's state and heartbeat files inside tmp_path."""
    monkeypatch.setenv("COLLECTOR_STATE_PATH", str(tmp_path / "collector-state.json"))
    monkeypatch.setenv("HEARTBEAT_PATH", str(tmp_path / "heartbeat"))


def make_orchestrator(monkeypatch):
    orchestrator = orchestrator_module.AlertOrchestrator()
    orchestrator.notification.send = AsyncMock()
    orchestrator.notification.aclose = AsyncMock()
    return orchestrator


def install_client(monkeypatch, login_behavior):
    """Patch SunsynkClient with a fake whose login() runs ``login_behavior``."""
    instances = []

    class FakeClient:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            self.closed = False
            instances.append(self)

        async def login(self):
            login_behavior(len(instances))

        async def close(self):
            self.closed = True

    sleep_mock = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "SunsynkClient", FakeClient)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "LOGIN_RETRY_WAIT_SECONDS", 900)
    monkeypatch.setattr(orchestrator_module, "AUTH_FAILURE_BACKOFF_SECONDS", 21600)
    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", sleep_mock)
    return instances, sleep_mock


@pytest.mark.asyncio
async def test_connect_client_with_retry_succeeds_on_second_attempt(monkeypatch):
    def behavior(attempt):
        if attempt == 1:
            raise LoginRateLimitedException("rate limited")

    instances, sleep_mock = install_client(monkeypatch, behavior)
    orchestrator = make_orchestrator(monkeypatch)

    client, retry_wait = await orchestrator.connect_client_with_retry()

    assert client is instances[1]
    assert retry_wait == 0
    assert instances[0].closed is True
    assert instances[1].closed is False
    sleep_mock.assert_awaited_once_with(900)
    orchestrator.notification.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [InvalidCredentialsException(), VerificationCodeRequiredException()]
)
async def test_auth_failure_alerts_immediately_without_a_second_attempt(monkeypatch, error):
    """Bad credentials must not be retried: retries provoke a verification-code lockout."""
    def behavior(_attempt):
        raise error

    instances, sleep_mock = install_client(monkeypatch, behavior)
    orchestrator = make_orchestrator(monkeypatch)

    client, retry_wait = await orchestrator.connect_client_with_retry()

    assert client is None
    assert len(instances) == 1
    assert instances[0].closed is True
    sleep_mock.assert_not_awaited()
    assert retry_wait == 21600

    orchestrator.notification.send.assert_awaited_once()
    _, kwargs = orchestrator.notification.send.await_args
    assert kwargs["category"] == "sunsynk_login_failure"
    assert kwargs["severity"] == "critical"
    assert kwargs["title"] == "🚨 Sunsynk Authentication Failed"
    assert kwargs["metadata"]["attempts"] == 1
    assert kwargs["metadata"]["retry_wait_seconds"] == 21600


@pytest.mark.asyncio
async def test_connectivity_failure_retries_then_alerts(monkeypatch):
    def behavior(_attempt):
        raise SunsynkConnectionError("internet down")

    instances, sleep_mock = install_client(monkeypatch, behavior)
    orchestrator = make_orchestrator(monkeypatch)

    client, retry_wait = await orchestrator.connect_client_with_retry()

    assert client is None
    assert retry_wait == 900
    assert len(instances) == 2
    assert all(instance.closed for instance in instances)
    sleep_mock.assert_awaited_once_with(900)

    orchestrator.notification.send.assert_awaited_once()
    _, kwargs = orchestrator.notification.send.await_args
    assert kwargs["title"] == "🚨 Sunsynk Connectivity Failed Twice"
    assert kwargs["metadata"]["attempts"] == 2


@pytest.mark.asyncio
async def test_unexpected_error_retries_then_alerts(monkeypatch):
    def behavior(_attempt):
        raise RuntimeError("unexpected")

    _, sleep_mock = install_client(monkeypatch, behavior)
    orchestrator = make_orchestrator(monkeypatch)

    client, retry_wait = await orchestrator.connect_client_with_retry()

    assert client is None
    assert retry_wait == 900
    sleep_mock.assert_awaited_once_with(900)
    _, kwargs = orchestrator.notification.send.await_args
    assert kwargs["title"] == "🚨 Sunsynk Login Failed Twice"


@pytest.mark.asyncio
async def test_monitor_loop_returns_when_credentials_missing(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", None)
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", None)

    orchestrator = make_orchestrator(monkeypatch)

    await orchestrator.monitor_loop()


@pytest.mark.asyncio
async def test_shutdown_closes_the_api_session(monkeypatch):
    orchestrator = make_orchestrator(monkeypatch)

    await orchestrator.shutdown()

    orchestrator.notification.aclose.assert_awaited_once()


def test_telemetry_and_alerts_share_one_api_client(monkeypatch):
    """The collector holds no storage credentials; zuva-api owns the database."""
    orchestrator = make_orchestrator(monkeypatch)

    assert orchestrator.telemetry.api_client is orchestrator.notification


def make_fake_client():
    fake_client = AsyncMock()
    fake_client.get_plants.return_value = [SimpleNamespace(id=10)]
    fake_client.get_inverters.return_value = [SimpleNamespace(sn="SN-1")]
    fake_client.get_inverter_realtime_battery.return_value = SimpleNamespace(
        soc=45, power=1.2, get_voltage=lambda: 52.0
    )
    fake_client.get_inverter_realtime_grid.return_value = SimpleNamespace(
        get_power=lambda: 0.0, get_voltage=lambda: 40.0, status=0
    )
    fake_client.get_inverter_realtime_output.return_value = SimpleNamespace(pac=3.1)
    fake_client.get_inverter_realtime_input.return_value = SimpleNamespace(get_power=lambda: 2.7)
    return fake_client


@pytest.mark.asyncio
async def test_poll_once_writes_telemetry_and_checks_alerts(monkeypatch):
    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.telemetry.write = AsyncMock()
    orchestrator.alerter.check_battery_alerts = AsyncMock()
    orchestrator.alerter.check_grid_alerts = AsyncMock()
    orchestrator.alerter.check_consumption_alerts = AsyncMock()

    await orchestrator.poll_once(make_fake_client())

    _, write_kwargs = orchestrator.telemetry.write.await_args
    assert write_kwargs["inverter_sn"] == "SN-1"
    assert write_kwargs["plant_id"] == 10
    assert write_kwargs["load_power_w"] == 3.1
    assert write_kwargs["grid_power_w"] == 0.0
    assert write_kwargs["battery_soc"] == 45.0
    assert write_kwargs["input_power_w"] == 2.7

    orchestrator.alerter.check_battery_alerts.assert_awaited_once_with(45.0)
    orchestrator.alerter.check_grid_alerts.assert_awaited_once_with(0.0, 40.0, 0)
    orchestrator.alerter.check_consumption_alerts.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_once_touches_the_heartbeat(monkeypatch):
    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.telemetry.write = AsyncMock()
    orchestrator.alerter.check_battery_alerts = AsyncMock()
    orchestrator.alerter.check_grid_alerts = AsyncMock()
    orchestrator.alerter.check_consumption_alerts = AsyncMock()

    from zuva.collector import heartbeat

    assert heartbeat.age_seconds() is None
    await orchestrator.poll_once(make_fake_client())
    assert heartbeat.age_seconds() is not None


@pytest.mark.asyncio
async def test_poll_once_stops_early_without_plants(monkeypatch):
    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.telemetry.write = AsyncMock()

    fake_client = AsyncMock()
    fake_client.get_plants.return_value = []

    await orchestrator.poll_once(fake_client)

    orchestrator.telemetry.write.assert_not_awaited()
    fake_client.get_inverters.assert_not_awaited()


@pytest.mark.asyncio
async def test_monitor_loop_polls_then_closes_the_client(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "POLL_INTERVAL", 1)

    orchestrator = make_orchestrator(monkeypatch)

    fake_client = make_fake_client()
    orchestrator.connect_client_with_retry = AsyncMock(return_value=(fake_client, 0))
    orchestrator.poll_once = AsyncMock()

    async def stop_after_first_cycle(_):
        raise asyncio.CancelledError()

    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", stop_after_first_cycle)

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.monitor_loop()

    orchestrator.poll_once.assert_awaited_once_with(fake_client)
    fake_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_monitor_loop_waits_the_returned_backoff_when_login_fails(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")

    orchestrator = make_orchestrator(monkeypatch)
    orchestrator.connect_client_with_retry = AsyncMock(return_value=(None, 21600))

    waits = []

    async def record_then_stop(seconds):
        waits.append(seconds)
        raise asyncio.CancelledError()

    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", record_then_stop)

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.monitor_loop()

    assert waits == [21600]


@pytest.mark.asyncio
async def test_monitor_loop_reconnects_after_an_auth_error_mid_poll(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")

    orchestrator = make_orchestrator(monkeypatch)
    fake_client = AsyncMock()
    orchestrator.poll_once = AsyncMock(side_effect=InvalidCredentialsException())

    # The inner loop breaks on the auth error, the client is closed, and the
    # outer loop reconnects rather than polling a dead session forever.
    orchestrator.connect_client_with_retry = AsyncMock(
        side_effect=[(fake_client, 0), asyncio.CancelledError()]
    )

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.monitor_loop()

    fake_client.close.assert_awaited_once()
    assert orchestrator.connect_client_with_retry.await_count == 2


@pytest.mark.asyncio
async def test_monitor_loop_keeps_polling_after_a_transient_error(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_USERNAME", "user")
    monkeypatch.setattr(orchestrator_module, "SUNSYNK_PASSWORD", "pass")
    monkeypatch.setattr(orchestrator_module, "POLL_INTERVAL", 5)

    orchestrator = make_orchestrator(monkeypatch)
    fake_client = AsyncMock()
    orchestrator.connect_client_with_retry = AsyncMock(return_value=(fake_client, 0))
    orchestrator.poll_once = AsyncMock(
        side_effect=[SunsynkConnectionError("blip"), None, asyncio.CancelledError()]
    )

    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(orchestrator_module.asyncio, "sleep", record_sleep)

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.monitor_loop()

    assert orchestrator.poll_once.await_count == 3
    assert sleeps == [5, 5]
