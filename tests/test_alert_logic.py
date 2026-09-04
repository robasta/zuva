from datetime import time, timedelta
from unittest.mock import AsyncMock

import pytest

from zuva.collector.alert_logic import AlertEvaluator
from zuva.collector.state_store import StateStore
from zuva.collector.timeutil import local_now

BASE_CONFIG = {
    'BATTERY_CRITICAL_THRESHOLD': 10,
    'BATTERY_LOW_THRESHOLD': 20,
    'BATTERY_RECOVERY_MARGIN': 5,
    'GRID_VOLTAGE_THRESHOLD': 50.0,
    'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
    'GRID_OUTAGE_COOLDOWN_MINUTES': 30,
    'EVENING_CONSUMPTION_THRESHOLD_W': 900,
    'HIGH_CONSUMPTION_THRESHOLD_W': 5,
}


def make_config(**overrides):
    config = dict(BASE_CONFIG)
    config.update(overrides)
    return config


def make_evaluator(**overrides):
    sender = AsyncMock()
    return AlertEvaluator(make_config(**overrides), sender), sender


@pytest.mark.asyncio
async def test_battery_critical_alert():
    evaluator, sender = make_evaluator()
    await evaluator.check_battery_alerts(9)
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_critical'
    assert kwargs['severity'] == 'critical'
    assert 'battery_soc' in kwargs['metadata']


@pytest.mark.asyncio
async def test_battery_low_alert():
    evaluator, sender = make_evaluator()
    await evaluator.check_battery_alerts(15)
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_low'
    assert kwargs['severity'] == 'high'
    assert 'battery_soc' in kwargs['metadata']


@pytest.mark.asyncio
async def test_battery_no_repeat_alert():
    evaluator, sender = make_evaluator()
    await evaluator.check_battery_alerts(9)
    await evaluator.check_battery_alerts(9)
    sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_battery_recovering_from_critical_into_low_band_is_silent():
    """Charging from 9% to 15% is good news, not a new alert."""
    evaluator, sender = make_evaluator()
    await evaluator.check_battery_alerts(9)
    sender.send.reset_mock()

    await evaluator.check_battery_alerts(15)

    sender.send.assert_not_awaited()
    assert evaluator.last_battery_alert == "critical"


@pytest.mark.asyncio
async def test_battery_rearms_only_after_recovery_margin():
    evaluator, sender = make_evaluator()
    await evaluator.check_battery_alerts(15)
    sender.send.reset_mock()

    # 22% is above the low threshold but inside the 5-point margin: still armed,
    # so a reading hovering on the boundary cannot flap.
    await evaluator.check_battery_alerts(22)
    assert evaluator.last_battery_alert == "low"

    await evaluator.check_battery_alerts(30)
    assert evaluator.last_battery_alert is None

    await evaluator.check_battery_alerts(15)
    sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_grid_outage_and_restore():
    evaluator, sender = make_evaluator(GRID_OUTAGE_CONSECUTIVE_READINGS=2)
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'grid_outage'
    assert kwargs['metadata']['reminder'] is False

    sender.send.reset_mock()
    await evaluator.check_grid_alerts(5.0, 230.0, 1)
    await evaluator.check_grid_alerts(5.0, 230.0, 1)
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'grid_restored'
    assert evaluator.grid_outage_blocked is False


@pytest.mark.asyncio
async def test_grid_outage_alerts_once_within_the_cooldown():
    evaluator, sender = make_evaluator(GRID_OUTAGE_CONSECUTIVE_READINGS=1)
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    sender.send.assert_awaited_once()
    sender.send.reset_mock()

    for _ in range(10):
        await evaluator.check_grid_alerts(0.0, 40.0, 0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_grid_outage_reminder_after_the_cooldown_elapses():
    evaluator, sender = make_evaluator(GRID_OUTAGE_CONSECUTIVE_READINGS=1)
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    sender.send.reset_mock()

    # Backdate the last alert past the 30 minute cooldown.
    evaluator.last_grid_outage_alert_at = local_now() - timedelta(minutes=31)

    await evaluator.check_grid_alerts(0.0, 40.0, 0)

    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'grid_outage'
    assert kwargs['metadata']['reminder'] is True
    assert kwargs['metadata']['minutes_offline'] == 31


@pytest.mark.asyncio
async def test_grid_outage_reminder_disabled_by_zero_cooldown():
    evaluator, sender = make_evaluator(
        GRID_OUTAGE_CONSECUTIVE_READINGS=1,
        GRID_OUTAGE_COOLDOWN_MINUTES=0,
    )
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    sender.send.reset_mock()
    evaluator.last_grid_outage_alert_at = local_now() - timedelta(hours=6)

    await evaluator.check_grid_alerts(0.0, 40.0, 0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_grid_alerts_ignore_missing_voltage():
    evaluator, sender = make_evaluator(GRID_OUTAGE_CONSECUTIVE_READINGS=1)
    await evaluator.check_grid_alerts(0.0, None, 0)
    sender.send.assert_not_awaited()
    assert evaluator.grid_outage_consecutive_count == 0


@pytest.mark.asyncio
async def test_consumption_alerts_evening_and_night():
    evaluator, sender = make_evaluator()

    await evaluator.check_consumption_alerts(1000, time(19, 0))
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'high_consumption'
    assert kwargs['severity'] == 'high'
    assert kwargs['metadata'] == {'load_power_w': 1000, 'limit_w': 900}

    sender.send.reset_mock()
    await evaluator.check_consumption_alerts(10, time(23, 0))
    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'high_consumption'
    assert kwargs['severity'] == 'critical'


@pytest.mark.asyncio
async def test_consumption_alerts_silent_during_daylight():
    evaluator, sender = make_evaluator()
    await evaluator.check_consumption_alerts(9999, time(12, 0))
    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_consumption_alerts_default_to_local_time(monkeypatch):
    """No explicit time means the configured timezone, never the container's UTC clock."""
    evaluator, sender = make_evaluator()
    monkeypatch.setattr(
        "zuva.collector.alert_logic.local_now",
        lambda: local_now().replace(hour=12, minute=0),
    )

    await evaluator.check_consumption_alerts(9999)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_config_keys_fall_back_to_defaults():
    sender = AsyncMock()
    evaluator = AlertEvaluator({}, sender)

    await evaluator.check_battery_alerts(5)

    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_critical'


@pytest.mark.asyncio
async def test_suppression_state_survives_a_restart(tmp_path):
    path = str(tmp_path / "state.json")
    sender = AsyncMock()
    evaluator = AlertEvaluator(make_config(), sender, state_store=StateStore(path))
    await evaluator.check_battery_alerts(9)
    sender.send.assert_awaited_once()

    # A fresh process reading the same state file must not re-alert.
    restarted_sender = AsyncMock()
    restarted = AlertEvaluator(make_config(), restarted_sender, state_store=StateStore(path))
    assert restarted.last_battery_alert == "critical"

    await restarted.check_battery_alerts(9)
    restarted_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_grid_outage_timestamp_round_trips_through_the_state_store(tmp_path):
    path = str(tmp_path / "state.json")
    sender = AsyncMock()
    evaluator = AlertEvaluator(
        make_config(GRID_OUTAGE_CONSECUTIVE_READINGS=1), sender, state_store=StateStore(path)
    )
    await evaluator.check_grid_alerts(0.0, 40.0, 0)

    restarted = AlertEvaluator(
        make_config(GRID_OUTAGE_CONSECUTIVE_READINGS=1), AsyncMock(), state_store=StateStore(path)
    )

    assert restarted.grid_outage_blocked is True
    assert restarted.last_grid_status is False
    assert restarted.last_grid_outage_alert_at is not None
    assert restarted.last_grid_outage_alert_at.tzinfo is not None
