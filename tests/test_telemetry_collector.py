import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zuva.collector.telemetry import TelemetryCollector


class CaptureClient:
    def __init__(self):
        self.readings = []

    async def send_telemetry(self, reading):
        self.readings.append(reading)


class ExplodingClient:
    async def send_telemetry(self, reading):
        raise RuntimeError("post failed")


@pytest.mark.asyncio
async def test_write_required_fields_only():
    client = CaptureClient()
    collector = TelemetryCollector(client)

    await collector.write(
        inverter_sn="SN1",
        plant_id=123,
        load_power_w=2.1,
        grid_power_w=1.3,
        battery_soc=57.0,
    )

    assert client.readings == [
        {
            "inverter_sn": "SN1",
            "plant_id": "123",
            "load_power_w": 2.1,
            "grid_power_w": 1.3,
            "battery_soc": 57.0,
        }
    ]


@pytest.mark.asyncio
async def test_write_includes_optional_fields():
    client = CaptureClient()
    collector = TelemetryCollector(client)

    await collector.write(
        inverter_sn="SN2",
        plant_id=999,
        load_power_w=3.5,
        grid_power_w=0.0,
        battery_soc=12.0,
        grid_voltage=230.0,
        grid_status=1,
        battery_power_w=-1.2,
        battery_voltage=52.4,
        input_power_w=4.7,
    )

    reading = client.readings[0]
    assert reading["grid_voltage"] == 230.0
    assert reading["grid_status"] == 1
    assert reading["battery_power_w"] == -1.2
    assert reading["battery_voltage"] == 52.4
    assert reading["input_power_w"] == 4.7


@pytest.mark.asyncio
async def test_missing_optional_fields_are_omitted_not_nulled():
    """A value the inverter did not report is not the same as zero."""
    client = CaptureClient()
    collector = TelemetryCollector(client)

    await collector.write(
        inverter_sn="SN3",
        plant_id=1,
        load_power_w=0.1,
        grid_power_w=0.0,
        battery_soc=99.0,
        grid_voltage=None,
        battery_power_w=48.0,
    )

    reading = client.readings[0]
    assert "grid_voltage" not in reading
    assert reading["battery_power_w"] == 48.0


@pytest.mark.asyncio
async def test_write_handles_post_error_without_raise():
    """Losing a reading must not stop the alert checks later in the poll."""
    collector = TelemetryCollector(ExplodingClient())

    await collector.write(
        inverter_sn="SN4",
        plant_id=1,
        load_power_w=0.1,
        grid_power_w=0.0,
        battery_soc=99.0,
    )


@pytest.mark.asyncio
async def test_watt_arguments_keep_their_unit_in_the_payload():
    """The stored names say watts, because the values are watts.

    The InfluxDB schema this replaced held watt values in ``*_kw`` fields; that
    mismatch went away with the measurement that pinned it.
    """
    client = CaptureClient()
    collector = TelemetryCollector(client)

    await collector.write(
        inverter_sn="SN5",
        plant_id=7,
        load_power_w=812.0,
        grid_power_w=-45.0,
        battery_soc=64.0,
    )

    reading = client.readings[0]
    assert reading["load_power_w"] == 812.0
    assert reading["grid_power_w"] == -45.0
    assert not [name for name in reading if name.endswith("_kw")]
