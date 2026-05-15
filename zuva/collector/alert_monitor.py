"""
Alert Monitor for Sunsynk Inverter
Monitors inverter data and triggers alerts based on thresholds
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, time, timedelta
import aiohttp

from influxdb_client import InfluxDBClient, Point
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

# Alert Thresholds
BATTERY_LOW_THRESHOLD = float(os.getenv("BATTERY_LOW_THRESHOLD", "20"))  # %
BATTERY_CRITICAL_THRESHOLD = float(os.getenv("BATTERY_CRITICAL_THRESHOLD", "10"))  # %
HIGH_CONSUMPTION_THRESHOLD = float(os.getenv("HIGH_CONSUMPTION_THRESHOLD", "5"))  # kW
EVENING_CONSUMPTION_THRESHOLD = float(os.getenv("EVENING_CONSUMPTION_THRESHOLD", "900"))  # kW
GRID_OUTAGE_CONSECUTIVE_READINGS = int(os.getenv("GRID_OUTAGE_CONSECUTIVE_READINGS", "3"))
GRID_VOLTAGE_THRESHOLD = float(os.getenv("GRID_VOLTAGE_THRESHOLD", "50.0"))
GRID_OUTAGE_COOLDOWN_MINUTES = int(os.getenv("GRID_OUTAGE_COOLDOWN_MINUTES", "30"))


class AlertMonitor:
    """Monitors solar data and sends alerts"""
    
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.query_api = None
        self.last_grid_status = None
        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count = 0
        self.last_grid_outage_alert_time = None
        self.last_battery_alert = None
        self.grid_outage_blocked = False  # Block further outage alerts until restore
        
    async def initialize(self):
        """Initialize InfluxDB connection"""
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.influx_client.query_api()
        logger.info("InfluxDB connection initialized")
    
    async def send_alert(self, category: str, severity: str, title: str, message: str, metadata: dict = None):
        """Send alert to notification service"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "metadata": metadata or {}
                }
                async with session.post(
                    f"{NOTIFICATION_API_URL}/alert",
                    json=payload,
                    params={"user_id": DEFAULT_USER_ID}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Alert sent: {category}")
                    else:
                        logger.error(f"Failed to send alert: {response.status}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def check_battery_alerts(self, battery_soc: float):
        """Check battery SOC and send alerts if needed"""
        # Critical battery
        if battery_soc <= BATTERY_CRITICAL_THRESHOLD:
            if self.last_battery_alert != "critical":
                await self.send_alert(
                    category="battery_critical",
                    severity="critical",
                    title="🚨 Critical Battery Level",
                    message=f"Battery is critically low at {battery_soc:.1f}%. Immediate attention required!",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "critical"
        
        # Low battery
        elif battery_soc <= BATTERY_LOW_THRESHOLD:
            if self.last_battery_alert != "low":
                await self.send_alert(
                    category="battery_low",
                    severity="high",
                    title="⚠️ Low Battery Level",
                    message=f"Battery is low at {battery_soc:.1f}%. Consider conserving energy.",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "low"
        
        # Reset alert status if battery recovers
        elif battery_soc > BATTERY_LOW_THRESHOLD + 5:  # Add hysteresis
            self.last_battery_alert = None
    
    async def check_grid_alerts(self, grid_power: float, grid_voltage: float | None, grid_status: int | None):
        """Check grid status and send alerts on outages/restoration"""

        # Missing voltage is ambiguous; do not change outage/restoration state.
        if grid_voltage is None:
            return

        grid_looks_down = abs(grid_power) <= 0.1 and grid_voltage < GRID_VOLTAGE_THRESHOLD

        if grid_looks_down:
            self.grid_restore_consecutive_count = 0
            if not self.grid_outage_blocked:
                self.grid_outage_consecutive_count += 1
                if self.grid_outage_consecutive_count == GRID_OUTAGE_CONSECUTIVE_READINGS:
                    await self.send_alert(
                        category="grid_outage",
                        severity="high",
                        title="⚡ Grid Outage Detected",
                        message="The grid has gone offline. Your system is now running on battery power.",
                        metadata={
                            "grid_power": grid_power,
                            "grid_voltage": grid_voltage,
                            "grid_status": grid_status,
                            "consecutive_readings": self.grid_outage_consecutive_count,
                        }
                    )
                    self.last_grid_outage_alert_time = datetime.now()
                    self.last_grid_status = False
                    self.grid_outage_blocked = True  # Block further outage alerts until restore
            return

        # Grid is up
        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count += 1

        if (
            self.last_grid_status is False
            and self.grid_restore_consecutive_count >= GRID_OUTAGE_CONSECUTIVE_READINGS
        ):
            await self.send_alert(
                category="grid_restored",
                severity="medium",
                title="✅ Grid Power Restored",
                message="Grid power has been restored. Normal operation resumed.",
                metadata={
                    "grid_power": grid_power,
                    "grid_voltage": grid_voltage,
                    "grid_status": grid_status,
                    "consecutive_readings": self.grid_restore_consecutive_count,
                }
            )
            self.grid_outage_blocked = False  # Allow outage alerts again
            self.last_grid_status = True
            self.grid_restore_consecutive_count = 0
        elif self.last_grid_status is None or self.last_grid_status is True:
            self.last_grid_status = True
    
    async def check_consumption_alerts(self, load_power: float):
        """Check for high consumption"""
        now = datetime.now().time()

        # Daytime (05:00-18:00): no alert due to sunlight
        if time(5, 0) <= now < time(18, 0):
            return

        # Evening (18:00-22:00): high severity if > 900 kW
        if time(18, 0) <= now < time(22, 0):
            if load_power > EVENING_CONSUMPTION_THRESHOLD:
                await self.send_alert(
                    category="high_consumption",
                    severity="high",
                    title="📊 High Energy Consumption",
                    message=f"Evening consumption is high at {load_power:.2f} kW (limit {EVENING_CONSUMPTION_THRESHOLD:.0f} kW).",
                    metadata={"load_power": load_power, "limit_kw": EVENING_CONSUMPTION_THRESHOLD}
                )
            return

        # Night (22:00-05:00): critical severity if above configured threshold
        if load_power > HIGH_CONSUMPTION_THRESHOLD:
            await self.send_alert(
                category="high_consumption",
                severity="critical",
                title="🚨 Critical Night Consumption",
                message=f"Night consumption is high at {load_power:.2f} kW (limit {HIGH_CONSUMPTION_THRESHOLD:.2f} kW).",
                metadata={"load_power": load_power, "limit_kw": HIGH_CONSUMPTION_THRESHOLD}
            )

    async def write_telemetry(
        self,
        inverter_sn: str,
        plant_id: int,
        load_power_kw: float,
        grid_power_kw: float,
        battery_soc: float,
        grid_voltage: float | None = None,
        grid_status: int | None = None,
        battery_power_kw: float | None = None,
        battery_voltage: float | None = None,
        input_power_kw: float | None = None,
    ):
        """Write telemetry data to InfluxDB for historical analysis"""
        try:
            point = Point("usage_readings") \
                .tag("inverter_sn", inverter_sn) \
                .tag("plant_id", str(plant_id)) \
                .field("load_power_kw", load_power_kw) \
                .field("grid_power_kw", grid_power_kw) \
                .field("battery_soc", battery_soc)

            # Add optional fields if present
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

            self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
            logger.debug(f"Telemetry written for inverter {inverter_sn}")
        except Exception as e:
            logger.error(f"Error writing telemetry: {e}")

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
                    await self.send_alert(
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
                    await self.send_alert(
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
        """Main monitoring loop"""
        if not SUNSYNK_USERNAME or not SUNSYNK_PASSWORD:
            logger.error("SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set")
            return
        
        await self.initialize()

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
                        plant_id = plants[0].id  # Extract plant_id for telemetry tagging

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
                        # Extract additional telemetry fields
                        battery_power_kw = float(getattr(battery, 'power', 0) or 0) if hasattr(battery, 'power') else None
                        battery_voltage = battery.get_voltage() if hasattr(battery, 'get_voltage') else None
                        battery_voltage = float(battery_voltage) if battery_voltage is not None else None
                        input_power_kw = input_data.get_power() if hasattr(input_data, 'get_power') else 0.0

                        logger.info(f"Battery: {battery_soc}%, Grid: {grid_power}kW, Load: {load_power}kW, Solar: {input_power_kw}kW")

                        # Write telemetry before alert checks
                        await self.write_telemetry(
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

                        await self.check_battery_alerts(battery_soc)
                        await self.check_grid_alerts(grid_power, grid_voltage, grid_status)
                        await self.check_consumption_alerts(load_power)

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
        """Cleanup resources"""
        if self.influx_client:
            self.influx_client.close()


async def main():
    """Main entry point"""
    monitor = AlertMonitor()
    try:
        await monitor.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        monitor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
