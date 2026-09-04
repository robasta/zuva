"""Telemetry for one poll.

UNITS: the inverter reports power in **watts**, and that is what is stored. The
field names now carry the unit (``load_power_w``); the InfluxDB schema this
replaced kept watt values in ``*_kw`` fields, a mismatch that only existed to
avoid splitting a series that no longer exists.

The collector owns no database. Each reading is POSTed to zuva-api, which writes
it to ``/data/zuva.db`` alongside the alert history, so there is one file to
mount and back up. A failed write is logged and dropped: telemetry is a record
of what happened, and losing a row must never stop the alert checks that follow
it in the poll.
"""
import logging

OPTIONAL_FIELDS = (
    'grid_voltage',
    'grid_status',
    'battery_power_w',
    'battery_voltage',
    'input_power_w',
)


class TelemetryCollector:
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)

    async def write(self, *, inverter_sn, plant_id, load_power_w, grid_power_w, battery_soc,
                    grid_voltage=None, grid_status=None, battery_power_w=None,
                    battery_voltage=None, input_power_w=None):
        reading = {
            'inverter_sn': inverter_sn,
            'plant_id': str(plant_id),
            'load_power_w': load_power_w,
            'grid_power_w': grid_power_w,
            'battery_soc': battery_soc,
        }
        optional = {
            'grid_voltage': grid_voltage,
            'grid_status': grid_status,
            'battery_power_w': battery_power_w,
            'battery_voltage': battery_voltage,
            'input_power_w': input_power_w,
        }
        # Omitted rather than sent as null: the inverter not reporting a value is
        # not the same as reporting zero.
        reading.update({name: optional[name] for name in OPTIONAL_FIELDS
                        if optional[name] is not None})

        try:
            await self.api_client.send_telemetry(reading)
            self.logger.debug("Telemetry sent for inverter %s", inverter_sn)
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error("Error sending telemetry: %s", error)
