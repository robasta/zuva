import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zuva.collector.telemetry import TelemetryCollector


class CaptureWriteApi:
    def __init__(self):
        self.bucket = None
        self.record = None

    def write(self, bucket, record):
        self.bucket = bucket
        self.record = record


class ExplodingWriteApi:
    def write(self, bucket, record):
        raise RuntimeError("write failed")


@pytest.mark.asyncio
async def test_write_required_fields_only():
    api = CaptureWriteApi()
    collector = TelemetryCollector(api, "solar_data")

    await collector.write(
        inverter_sn="SN1",
        plant_id=123,
        load_power_kw=2.1,
        grid_power_kw=1.3,
        battery_soc=57.0,
    )

    assert api.bucket == "solar_data"
    line = api.record.to_line_protocol()
    assert "usage_readings" in line
    assert "inverter_sn=SN1" in line
    assert "plant_id=123" in line
    assert "load_power_kw=2.1" in line
    assert "grid_power_kw=1.3" in line
    assert "battery_soc=57" in line


@pytest.mark.asyncio
async def test_write_includes_optional_fields():
    api = CaptureWriteApi()
    collector = TelemetryCollector(api, "solar_data")

    await collector.write(
        inverter_sn="SN2",
        plant_id=999,
        load_power_kw=3.5,
        grid_power_kw=0.0,
        battery_soc=12.0,
        grid_voltage=230.0,
        grid_status=1,
        battery_power_kw=-1.2,
        battery_voltage=52.4,
        input_power_kw=4.7,
    )

    line = api.record.to_line_protocol()
    assert "grid_voltage=230" in line
    assert "grid_status=1i" in line
    assert "battery_power_kw=-1.2" in line
    assert "battery_voltage=52.4" in line
    assert "input_power_kw=4.7" in line


@pytest.mark.asyncio
async def test_write_handles_write_error_without_raise():
    collector = TelemetryCollector(ExplodingWriteApi(), "solar_data")

    await collector.write(
        inverter_sn="SN3",
        plant_id=1,
        load_power_kw=0.1,
        grid_power_kw=0.0,
        battery_soc=99.0,
    )
