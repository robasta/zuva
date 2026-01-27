"""
Alert Monitor for Sunsynk Inverter
Monitors inverter data and triggers alerts based on thresholds
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, time
from typing import Optional
import aiohttp

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# Add parent directory to path to import sunsynk client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from sunsynk import SunsynkClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SUNSYNK_USERNAME = os.getenv("SUNSYNK_USERNAME")
SUNSYNK_PASSWORD = os.getenv("SUNSYNK_PASSWORD")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "sunsynk-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sunsynk")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "solar_data")

NOTIFICATION_API_URL = os.getenv("NOTIFICATION_API_URL", "http://notification-api:8000")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")

# Alert Thresholds
BATTERY_LOW_THRESHOLD = float(os.getenv("BATTERY_LOW_THRESHOLD", "20"))  # %
BATTERY_CRITICAL_THRESHOLD = float(os.getenv("BATTERY_CRITICAL_THRESHOLD", "10"))  # %
HIGH_CONSUMPTION_THRESHOLD = float(os.getenv("HIGH_CONSUMPTION_THRESHOLD", "5"))  # kW


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
        now = datetime.now()
        
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
            if load_power > 900:
                await self.send_alert(
                    category="high_consumption",
                    severity="high",
                    title="📊 High Energy Consumption",
                    message=f"Evening consumption is high at {load_power:.2f} kW (limit 900 kW).",
                    metadata={"load_power": load_power, "limit_kw": 900}
                )
            return

        # Night (23:00-06:00): critical severity if > 400 kW
        if load_power > 400:
            await self.send_alert(
                category="high_consumption",
                severity="critical",
                title="🚨 Critical Night Consumption",
                message=f"Night consumption is high at {load_power:.2f} kW (limit 400 kW).",
                metadata={"load_power": load_power, "limit_kw": 400}
            )
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        if not SUNSYNK_USERNAME or not SUNSYNK_PASSWORD:
            logger.error("SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set")
            return
        
        await self.initialize()
        
        async with SunsynkClient(SUNSYNK_USERNAME, SUNSYNK_PASSWORD) as client:
            logger.info("Connected to Sunsynk API")
            
            while True:
                try:
                    # Get plants
                    plants = await client.get_plants()
                    if not plants:
                        logger.warning("No plants found")
                        await asyncio.sleep(POLL_INTERVAL)
                        continue
                    
                    plant = plants[0]
                    
                    # Get inverters
                    inverters = await client.get_inverters()
                    if not inverters:
                        logger.warning("No inverters found")
                        await asyncio.sleep(POLL_INTERVAL)
                        continue
                    
                    inverter = inverters[0]
                    
                    # Get current data
                    battery = await client.get_inverter_realtime_battery(inverter.sn)
                    grid = await client.get_inverter_realtime_grid(inverter.sn)
                    output = await client.get_inverter_realtime_output(inverter.sn)
                    
                    # Extract metrics
                    battery_soc = float(getattr(battery, 'soc', 0) or 0)
                    grid_power = grid.get_power() if hasattr(grid, 'get_power') else float(getattr(grid, 'pac', 0) or 0)
                    grid_power = float(grid_power or 0)
                    load_power = float(getattr(output, 'pac', 0) or 0)
                    
                    logger.info(f"Battery: {battery_soc}%, Grid: {grid_power}kW, Load: {load_power}kW")
                    
                    # Check for alerts
                    await self.check_battery_alerts(battery_soc)
                    await self.check_grid_alerts(grid_power)
                    await self.check_consumption_alerts(load_power)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                
                await asyncio.sleep(POLL_INTERVAL)
    
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
