import pytest
from unittest.mock import AsyncMock
from zuva.collector.alert_logic import AlertEvaluator

@pytest.mark.asyncio
async def test_battery_critical_alert():
    sender = AsyncMock()
    config = {
        'BATTERY_CRITICAL_THRESHOLD': 10,
        'BATTERY_LOW_THRESHOLD': 20,
        'GRID_VOLTAGE_THRESHOLD': 50.0,
        'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
        'EVENING_CONSUMPTION_THRESHOLD': 900,
        'HIGH_CONSUMPTION_THRESHOLD': 5,
    }
    evaluator = AlertEvaluator(config, sender)
    await evaluator.check_battery_alerts(9)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_critical'
    assert kwargs['severity'] == 'critical'
    assert 'battery_soc' in kwargs['metadata']

@pytest.mark.asyncio
async def test_battery_low_alert():
    sender = AsyncMock()
    config = {
        'BATTERY_CRITICAL_THRESHOLD': 10,
        'BATTERY_LOW_THRESHOLD': 20,
        'GRID_VOLTAGE_THRESHOLD': 50.0,
        'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
        'EVENING_CONSUMPTION_THRESHOLD': 900,
        'HIGH_CONSUMPTION_THRESHOLD': 5,
    }
    evaluator = AlertEvaluator(config, sender)
    await evaluator.check_battery_alerts(15)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'battery_low'
    assert kwargs['severity'] == 'high'
    assert 'battery_soc' in kwargs['metadata']

@pytest.mark.asyncio
async def test_battery_no_repeat_alert():
    sender = AsyncMock()
    config = {
        'BATTERY_CRITICAL_THRESHOLD': 10,
        'BATTERY_LOW_THRESHOLD': 20,
        'GRID_VOLTAGE_THRESHOLD': 50.0,
        'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
        'EVENING_CONSUMPTION_THRESHOLD': 900,
        'HIGH_CONSUMPTION_THRESHOLD': 5,
    }
    evaluator = AlertEvaluator(config, sender)
    await evaluator.check_battery_alerts(9)
    await evaluator.check_battery_alerts(9)
    sender.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_grid_outage_and_restore():
    sender = AsyncMock()
    config = {
        'BATTERY_CRITICAL_THRESHOLD': 10,
        'BATTERY_LOW_THRESHOLD': 20,
        'GRID_VOLTAGE_THRESHOLD': 50.0,
        'GRID_OUTAGE_CONSECUTIVE_READINGS': 2,
        'EVENING_CONSUMPTION_THRESHOLD': 900,
        'HIGH_CONSUMPTION_THRESHOLD': 5,
    }
    evaluator = AlertEvaluator(config, sender)
    # Simulate grid outage
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    await evaluator.check_grid_alerts(0.0, 40.0, 0)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'grid_outage'
    # Simulate grid restore
    sender.send.reset_mock()
    evaluator.last_grid_status = False
    await evaluator.check_grid_alerts(5.0, 230.0, 1)
    await evaluator.check_grid_alerts(5.0, 230.0, 1)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'grid_restored'

@pytest.mark.asyncio
async def test_consumption_alerts_evening_and_night():
    sender = AsyncMock()
    config = {
        'BATTERY_CRITICAL_THRESHOLD': 10,
        'BATTERY_LOW_THRESHOLD': 20,
        'GRID_VOLTAGE_THRESHOLD': 50.0,
        'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
        'EVENING_CONSUMPTION_THRESHOLD': 900,
        'HIGH_CONSUMPTION_THRESHOLD': 5,
    }
    evaluator = AlertEvaluator(config, sender)
    from datetime import time
    # Evening high consumption
    await evaluator.check_consumption_alerts(1000, time(19, 0), config)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'high_consumption'
    assert kwargs['severity'] == 'high'
    sender.send.reset_mock()
    # Night critical consumption
    await evaluator.check_consumption_alerts(10, time(23, 0), config)
    sender.send.assert_awaited_once()
    args, kwargs = sender.send.await_args
    assert kwargs['category'] == 'high_consumption'
    assert kwargs['severity'] == 'critical'
