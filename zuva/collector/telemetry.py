"""Telemetry writes for the ``usage_readings`` measurement.

UNITS: the inverter reports power in **watts**, and that is what is stored.
The InfluxDB field names still end in ``_kw`` for historical reasons - renaming
them would break every existing dashboard query and split the series, so the
mapping from watt-valued arguments to legacy field names is made explicit here
instead. Read these fields as watts.
"""
import logging

from influxdb_client import Point

# Python argument name -> InfluxDB field name (legacy names retained on purpose).
FIELD_NAMES = {
    'load_power_w': 'load_power_kw',
    'grid_power_w': 'grid_power_kw',
    'battery_soc': 'battery_soc',
    'grid_voltage': 'grid_voltage',
    'grid_status': 'grid_status',
    'battery_power_w': 'battery_power_kw',
    'battery_voltage': 'battery_voltage',
    'input_power_w': 'input_power_kw',
}


class TelemetryCollector:
    def __init__(self, write_api, bucket):
        self.write_api = write_api
        self.bucket = bucket
        self.logger = logging.getLogger(__name__)

    async def write(self, *, inverter_sn, plant_id, load_power_w, grid_power_w, battery_soc,
                    grid_voltage=None, grid_status=None, battery_power_w=None,
                    battery_voltage=None, input_power_w=None):
        try:
            point = Point("usage_readings") \
                .tag("inverter_sn", inverter_sn) \
                .tag("plant_id", str(plant_id)) \
                .field(FIELD_NAMES['load_power_w'], load_power_w) \
                .field(FIELD_NAMES['grid_power_w'], grid_power_w) \
                .field(FIELD_NAMES['battery_soc'], battery_soc)
            optional = {
                'grid_voltage': grid_voltage,
                'grid_status': grid_status,
                'battery_power_w': battery_power_w,
                'battery_voltage': battery_voltage,
                'input_power_w': input_power_w,
            }
            for arg_name, value in optional.items():
                if value is not None:
                    point = point.field(FIELD_NAMES[arg_name], value)
            self.write_api.write(bucket=self.bucket, record=point)
            self.logger.debug("Telemetry written for inverter %s", inverter_sn)
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error("Error writing telemetry: %s", error)
