"""
Alert Monitor for Sunsynk Inverter
Monitors inverter data and triggers alerts based on thresholds
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, time
import aiohttp

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


class AlertMonitor:
    """Monitors solar data and sends alerts"""
    
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.query_api = None
        self.last_grid_status = None
        self.last_battery_alert = None
        
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
    
    async def check_grid_alerts(self, grid_power: float):
        """Check grid status and send alerts on outages/restoration"""
        grid_active = abs(grid_power) > 0.1  # Grid is active if power flow > 0.1 kW
        
        # Grid outage detected
        if not grid_active and self.last_grid_status is True:
            await self.send_alert(
                category="grid_outage",
                severity="high",
                title="⚡ Grid Outage Detected",
                message="The grid has gone offline. Your system is now running on battery power.",
                metadata={"grid_power": grid_power}
            )
        
        # Grid restored
        elif grid_active and self.last_grid_status is False:
            await self.send_alert(
                category="grid_restored",
                severity="medium",
                title="✅ Grid Power Restored",
                message="Grid power has been restored. Normal operation resumed.",
                metadata={"grid_power": grid_power}
            )
        
        self.last_grid_status = grid_active
    
    async def check_consumption_alerts(self, load_power: float):
        """Check for high consumption"""
        now = datetime.now().time()

        # Daytime (06:00-18:00): no alert due to sunlight
        if time(6, 0) <= now < time(18, 0):
            return

        # Evening (18:00-23:00): high severity if > 900 kW
        if time(18, 0) <= now < time(23, 0):
            if load_power > EVENING_CONSUMPTION_THRESHOLD:
                await self.send_alert(
                    category="high_consumption",
                    severity="high",
                    title="📊 High Energy Consumption",
                    message=f"Evening consumption is high at {load_power:.2f} kW (limit {EVENING_CONSUMPTION_THRESHOLD:.0f} kW).",
                    metadata={"load_power": load_power, "limit_kw": EVENING_CONSUMPTION_THRESHOLD}
                )
            return

        # Night (23:00-06:00): critical severity if above configured threshold
        if load_power > HIGH_CONSUMPTION_THRESHOLD:
            await self.send_alert(
                category="high_consumption",
                severity="critical",
                title="🚨 Critical Night Consumption",
                message=f"Night consumption is high at {load_power:.2f} kW (limit {HIGH_CONSUMPTION_THRESHOLD:.2f} kW).",
                metadata={"load_power": load_power, "limit_kw": HIGH_CONSUMPTION_THRESHOLD}
            )

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

                        battery = await client.get_inverter_realtime_battery(inverter.sn)
                        grid = await client.get_inverter_realtime_grid(inverter.sn)
                        output = await client.get_inverter_realtime_output(inverter.sn)

                        battery_soc = float(getattr(battery, 'soc', 0) or 0)
                        grid_power = grid.get_power() if hasattr(grid, 'get_power') else float(getattr(grid, 'pac', 0) or 0)
                        grid_power = float(grid_power or 0)
                        load_power = float(getattr(output, 'pac', 0) or 0)

                        logger.info(f"Battery: {battery_soc}%, Grid: {grid_power}kW, Load: {load_power}kW")

                        await self.check_battery_alerts(battery_soc)
                        await self.check_grid_alerts(grid_power)
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
