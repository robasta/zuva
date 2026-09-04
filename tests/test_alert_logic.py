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


def feed_discharge(evaluator, readings):
    """Replay ``(minutes_ago, soc)`` samples onto the rolling SoC window.

    Timestamps come off local_now() because the runners are UTC while TIMEZONE
    defaults to Africa/Johannesburg; a naive datetime.now() would be two hours
    out of step with the production code under test.
    """
    now = local_now()
    for minutes_ago, soc in readings:
        evaluator.record_soc_sample(soc, at=now - timedelta(minutes=minutes_ago))


@pytest.mark.asyncio
async def test_depletion_is_silent_until_the_window_is_wide_enough():
    """A cold start has no slope, so it must not guess at one."""
    evaluator, sender = make_evaluator()
    feed_discharge(evaluator, [(10, 40.0), (0, 36.0)])

    assert evaluator.soc_discharge_rate() is None
    await evaluator.check_battery_depletion(36.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_warns_before_the_low_threshold():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    # 6%/hour from 30% leaves 10 points to the 20% reserve: 100 minutes, inside
    # the 120-minute horizon but outside the 60-minute urgent window.
    feed_discharge(evaluator, [(30, 33.0), (15, 31.5), (0, 30.0)])

    await evaluator.check_battery_depletion(30.0)

    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_depletion'
    assert kwargs['severity'] == 'high'
    assert kwargs['metadata']['reserve_soc'] == 20
    assert kwargs['metadata']['discharge_rate_pct_per_hour'] == 6.0
    assert kwargs['metadata']['minutes_to_reserve'] == 100
    assert '20%' in kwargs['message']


@pytest.mark.asyncio
async def test_depletion_requires_consecutive_readings():
    """One steep reading is not an episode; two in a row are."""
    evaluator, sender = make_evaluator()
    feed_discharge(evaluator, [(30, 33.0), (15, 31.5), (0, 30.0)])

    await evaluator.check_battery_depletion(30.0)
    sender.send.assert_not_awaited()

    await evaluator.check_battery_depletion(30.0)
    sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_depletion_escalates_to_critical_then_stays_quiet():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 33.0), (15, 31.5), (0, 30.0)])
    await evaluator.check_battery_depletion(30.0)
    sender.send.reset_mock()

    # 25% at the same 6%/hour is 50 minutes from the reserve: inside the urgent
    # window, so this escalates even though a warning already went out.
    await evaluator.check_battery_depletion(25.0)

    sender.send.assert_awaited_once()
    _, kwargs = sender.send.await_args
    assert kwargs['severity'] == 'critical'
    assert evaluator.last_depletion_alert == 'urgent'

    sender.send.reset_mock()
    for _ in range(5):
        await evaluator.check_battery_depletion(24.0)
    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_does_not_step_back_down_to_a_warning():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 31.0), (15, 29.5), (0, 28.0)])
    await evaluator.check_battery_depletion(24.0)
    assert evaluator.last_depletion_alert == 'urgent'
    sender.send.reset_mock()

    # A later reading projecting further out must not re-announce the warning.
    await evaluator.check_battery_depletion(30.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_is_silent_while_charging():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 34.0), (15, 37.0), (0, 40.0)])

    assert evaluator.soc_discharge_rate() is None
    await evaluator.check_battery_depletion(40.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_ignores_a_rate_below_the_noise_floor():
    """A flat SoC divides out into an absurd horizon, so it must not project."""
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 34.2), (15, 34.1), (0, 34.0)])

    assert evaluator.soc_discharge_rate() is None
    await evaluator.check_battery_depletion(34.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_defers_to_battery_low_below_the_reserve():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 22.0), (15, 20.5), (0, 19.0)])

    await evaluator.check_battery_depletion(19.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_depletion_re_arms_once_the_discharge_stops():
    evaluator, sender = make_evaluator(BATTERY_DEPLETION_CONSECUTIVE_READINGS=1)
    feed_discharge(evaluator, [(30, 33.0), (15, 31.5), (0, 30.0)])
    await evaluator.check_battery_depletion(30.0)
    assert evaluator.last_depletion_alert == 'warning'

    # Solar comes up and the pack recharges: the window now slopes the other way.
    evaluator.soc_samples = []
    feed_discharge(evaluator, [(25, 40.0), (0, 45.0)])
    await evaluator.check_battery_depletion(45.0)

    assert evaluator.last_depletion_alert is None
    assert evaluator.depletion_consecutive_count == 0


@pytest.mark.asyncio
async def test_depletion_can_be_disabled_with_a_zero_horizon():
    evaluator, sender = make_evaluator(
        BATTERY_DEPLETION_CONSECUTIVE_READINGS=1,
        BATTERY_DEPLETION_HORIZON_MINUTES=0,
    )
    feed_discharge(evaluator, [(30, 37.0), (15, 35.5), (0, 34.0)])

    await evaluator.check_battery_depletion(34.0)

    sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_battery_low_gains_a_time_to_critical_clause():
    evaluator, sender = make_evaluator()
    feed_discharge(evaluator, [(30, 21.0), (15, 19.5), (0, 18.0)])

    await evaluator.check_battery_alerts(18.0)

    _, kwargs = sender.send.await_args
    assert 'to critical at the current 6.0%/hour' in kwargs['message']
    assert kwargs['metadata']['minutes_to_next_threshold'] == 80


@pytest.mark.asyncio
async def test_battery_alerts_are_unchanged_without_a_rate():
    """No slope yet means the original message text, byte for byte."""
    evaluator, sender = make_evaluator()

    await evaluator.check_battery_alerts(15.0)

    _, kwargs = sender.send.await_args
    assert kwargs['message'] == "Battery is low at 15.0%. Consider conserving energy."
    assert kwargs['metadata'] == {"battery_soc": 15.0}


@pytest.mark.asyncio
async def test_the_soc_window_survives_a_restart(tmp_path):
    """Rebuilding the window from scratch would blind the projection for 20 min."""
    path = str(tmp_path / "state.json")
    evaluator = AlertEvaluator(make_config(), AsyncMock(), state_store=StateStore(path))
    feed_discharge(evaluator, [(30, 37.0), (15, 35.5), (0, 34.0)])
    evaluator.record_soc_sample(34.0)

    restarted = AlertEvaluator(make_config(), AsyncMock(), state_store=StateStore(path))

    assert len(restarted.soc_samples) == len(evaluator.soc_samples)
    assert all(at.tzinfo is not None for at, _ in restarted.soc_samples)
    assert restarted.soc_discharge_rate() == pytest.approx(6.0, abs=0.1)


def test_stale_and_malformed_soc_samples_are_dropped_on_load(tmp_path):
    path = str(tmp_path / "state.json")
    stale = (local_now() - timedelta(hours=4)).isoformat()
    fresh = (local_now() - timedelta(minutes=5)).isoformat()
    StateStore(path).save({
        "soc_samples": [
            [stale, 90.0],
            ["not-a-timestamp", 50.0],
            [fresh],
            [fresh, "not-a-number"],
            "garbage",
            [fresh, 34.0],
        ]
    })

    evaluator = AlertEvaluator(make_config(), AsyncMock(), state_store=StateStore(path))

    assert [soc for _, soc in evaluator.soc_samples] == [34.0]


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
