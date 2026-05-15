import logging
from influxdb_client import Point

class TelemetryCollector:
    def __init__(self, write_api, bucket):
        self.write_api = write_api
        self.bucket = bucket
        self.logger = logging.getLogger(__name__)

    async def write(self, *, inverter_sn, plant_id, load_power_kw, grid_power_kw, battery_soc, grid_voltage=None, grid_status=None, battery_power_kw=None, battery_voltage=None, input_power_kw=None):
        try:
            point = Point("usage_readings") \
                .tag("inverter_sn", inverter_sn) \
                .tag("plant_id", str(plant_id)) \
                .field("load_power_kw", load_power_kw) \
                .field("grid_power_kw", grid_power_kw) \
                .field("battery_soc", battery_soc)
            if grid_voltage is not None:
                point = point.field("grid_voltage", grid_voltage)
            if grid_status is not None:
                point = point.field("grid_status", grid_status)
            if battery_power_kw is not None:
                point = point.field("battery_power_kw", battery_power_kw)
            if battery_voltage is not None:
                point = point.field("battery_voltage", battery_voltage)
            if input_power_kw is not None:
                point = point.field("input_power_kw", input_power_kw)
            self.write_api.write(bucket=self.bucket, record=point)
            self.logger.debug(f"Telemetry written for inverter {inverter_sn}")
        except Exception as e:
            self.logger.error(f"Error writing telemetry: {e}")
