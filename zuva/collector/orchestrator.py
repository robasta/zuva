
"""
Alert Orchestrator for Sunsynk Inverter
Coordinates telemetry, alert logic, and notification
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# Add parent directory to path to import sunsynk client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from sunsynk import SunsynkClient
from sunsynk.client import (
    InvalidCredentialsException,
    LoginRateLimitedException,
    SunsynkApiError,
    SunsynkConnectionError,
    SunsynkTimeoutError,
    VerificationCodeRequiredException,
)

from .telemetry import TelemetryCollector
from .alert_logic import AlertEvaluator
from .notification import NotificationSender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SUNSYNK_USERNAME = os.getenv("SUNSYNK_USERNAME")
SUNSYNK_PASSWORD = os.getenv("SUNSYNK_PASSWORD")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
LOGIN_RETRY_WAIT_SECONDS = int(os.getenv("LOGIN_RETRY_WAIT_SECONDS", "900"))


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "sunsynk-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sunsynk")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "solar_data")

NOTIFICATION_API_URL = os.getenv("NOTIFICATION_API_URL", "http://zuva-api:8000")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")

# Alert Thresholds config dict for injection
ALERT_CONFIG = {
    'BATTERY_LOW_THRESHOLD': float(os.getenv("BATTERY_LOW_THRESHOLD", "20")),
    'BATTERY_CRITICAL_THRESHOLD': float(os.getenv("BATTERY_CRITICAL_THRESHOLD", "10")),
    'HIGH_CONSUMPTION_THRESHOLD': float(os.getenv("HIGH_CONSUMPTION_THRESHOLD", "5")),
    'EVENING_CONSUMPTION_THRESHOLD': float(os.getenv("EVENING_CONSUMPTION_THRESHOLD", "900")),
    'GRID_OUTAGE_CONSECUTIVE_READINGS': int(os.getenv("GRID_OUTAGE_CONSECUTIVE_READINGS", "3")),
    'GRID_VOLTAGE_THRESHOLD': float(os.getenv("GRID_VOLTAGE_THRESHOLD", "50.0")),
    'GRID_OUTAGE_COOLDOWN_MINUTES': int(os.getenv("GRID_OUTAGE_COOLDOWN_MINUTES", "30")),
}




class AlertOrchestrator:
    def __init__(self):
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.influx_client.query_api()
        self.telemetry = TelemetryCollector(self.write_api, INFLUXDB_BUCKET)
        self.notification = NotificationSender(NOTIFICATION_API_URL, DEFAULT_USER_ID)
        self.alerter = AlertEvaluator(ALERT_CONFIG, self.notification)

    async def connect_client_with_retry(self):
        last_error = None
        for attempt in (1, 2):
            client = SunsynkClient(SUNSYNK_USERNAME, SUNSYNK_PASSWORD)
            try:
                await client.login()
                logger.info("Connected to Sunsynk API")
                return client
            except (SunsynkTimeoutError, SunsynkConnectionError, SunsynkApiError) as error:
                last_error = error
                await client.close()
                if attempt == 1:
                    logger.warning(
                        "Sunsynk connectivity attempt 1 failed: %s. Retrying in %s seconds.",
                        error,
                        LOGIN_RETRY_WAIT_SECONDS,
                    )
                    await asyncio.sleep(LOGIN_RETRY_WAIT_SECONDS)
                else:
                    logger.critical("Sunsynk connectivity attempt 2 failed: %s", error)
                    await self.notification.send(
                        category="sunsynk_login_failure",
                        severity="critical",
                        title="🚨 Sunsynk Connectivity Failed Twice",
                        message=(
                            "Unable to reach Sunsynk API after retry. "
                            f"Second failure: {error}."
                        ),
                        metadata={
                            "attempts": 2,
                            "retry_wait_seconds": LOGIN_RETRY_WAIT_SECONDS,
                            "error": str(error),
                        },
                    )
            except Exception as error:
                last_error = error
                await client.close()
                if attempt == 1:
                    logger.warning(
                        "Sunsynk login attempt 1 failed: %s. Retrying in %s seconds.",
                        error,
                        LOGIN_RETRY_WAIT_SECONDS,
                    )
                    await asyncio.sleep(LOGIN_RETRY_WAIT_SECONDS)
                else:
                    logger.critical("Sunsynk login attempt 2 failed: %s", error)
                    await self.notification.send(
                        category="sunsynk_login_failure",
                        severity="critical",
                        title="🚨 Sunsynk Login Failed Twice",
                        message=(
                            "Sunsynk login failed after retry. "
                            f"Second failure: {error}."
                        ),
                        metadata={
                            "attempts": 2,
                            "retry_wait_seconds": LOGIN_RETRY_WAIT_SECONDS,
                            "error": str(error),
                        },
                    )
        logger.error("Unable to connect to Sunsynk API after retries: %s", last_error)
        return None

    async def monitor_loop(self):
        if not SUNSYNK_USERNAME or not SUNSYNK_PASSWORD:
            logger.error("SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set")
            return
        logger.info("InfluxDB connection initialized")
        while True:
            client = await self.connect_client_with_retry()
            if client is None:
                await asyncio.sleep(LOGIN_RETRY_WAIT_SECONDS)
                continue
            try:
                while True:
                    try:
                        plants = await client.get_plants()
                        if not plants:
                            logger.warning("No plants found")
                            await asyncio.sleep(POLL_INTERVAL)
                            continue
                        inverters = await client.get_inverters()
                        if not inverters:
                            logger.warning("No inverters found")
                            await asyncio.sleep(POLL_INTERVAL)
                            continue
                        inverter = inverters[0]
                        plant_id = plants[0].id
                        battery = await client.get_inverter_realtime_battery(inverter.sn)
                        grid = await client.get_inverter_realtime_grid(inverter.sn)
                        output = await client.get_inverter_realtime_output(inverter.sn)
                        input_data = await client.get_inverter_realtime_input(inverter.sn)
                        battery_soc = float(getattr(battery, 'soc', 0) or 0)
                        grid_power = grid.get_power() if hasattr(grid, 'get_power') else float(getattr(grid, 'pac', 0) or 0)
                        grid_power = float(grid_power or 0)
                        grid_voltage = grid.get_voltage()
                        grid_voltage = float(grid_voltage) if grid_voltage is not None else None
                        grid_status = getattr(grid, 'status', None)
                        load_power = float(getattr(output, 'pac', 0) or 0)
                        battery_power_kw = float(getattr(battery, 'power', 0) or 0) if hasattr(battery, 'power') else None
                        battery_voltage = battery.get_voltage() if hasattr(battery, 'get_voltage') else None
                        battery_voltage = float(battery_voltage) if battery_voltage is not None else None
                        input_power_kw = input_data.get_power() if hasattr(input_data, 'get_power') else 0.0
                        logger.info(f"Battery: {battery_soc}%, Grid: {grid_power}kW, Load: {load_power}kW, Solar: {input_power_kw}kW")
                        await self.telemetry.write(
                            inverter_sn=inverter.sn,
                            plant_id=plant_id,
                            load_power_kw=load_power,
                            grid_power_kw=grid_power,
                            battery_soc=battery_soc,
                            grid_voltage=grid_voltage,
                            grid_status=grid_status,
                            battery_power_kw=battery_power_kw,
                            battery_voltage=battery_voltage,
                            input_power_kw=input_power_kw,
                        )
                        now = datetime.now().time()
                        await self.alerter.check_battery_alerts(battery_soc)
                        await self.alerter.check_grid_alerts(grid_power, grid_voltage, grid_status)
                        await self.alerter.check_consumption_alerts(load_power, now, ALERT_CONFIG)
                    except (
                        LoginRateLimitedException,
                        InvalidCredentialsException,
                        VerificationCodeRequiredException,
                    ) as auth_error:
                        logger.error("Authentication error in monitoring loop: %s", auth_error, exc_info=True)
                        break
                    except (SunsynkTimeoutError, SunsynkConnectionError, SunsynkApiError) as network_error:
                        logger.warning("Connectivity error in monitoring loop: %s", network_error, exc_info=True)
                    except Exception as e:
                        logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                    await asyncio.sleep(POLL_INTERVAL)
            finally:
                await client.close()

    def shutdown(self):
        if self.influx_client:
            self.influx_client.close()



async def main():
    orchestrator = AlertOrchestrator()
    try:
        await orchestrator.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
