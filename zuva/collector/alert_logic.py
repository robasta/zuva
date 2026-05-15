import logging

class AlertEvaluator:
    def __init__(self, config, notification_sender):
        self.config = config
        self.notification_sender = notification_sender
        self.logger = logging.getLogger(__name__)
        self.last_battery_alert = None
        self.last_grid_status = None
        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count = 0
        self.grid_outage_blocked = False

    async def check_battery_alerts(self, battery_soc):
        if battery_soc <= self.config['BATTERY_CRITICAL_THRESHOLD']:
            if self.last_battery_alert != "critical":
                await self.notification_sender.send(
                    category="battery_critical",
                    severity="critical",
                    title="🚨 Critical Battery Level",
                    message=f"Battery is critically low at {battery_soc:.1f}%. Immediate attention required!",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "critical"
        elif battery_soc <= self.config['BATTERY_LOW_THRESHOLD']:
            if self.last_battery_alert != "low":
                await self.notification_sender.send(
                    category="battery_low",
                    severity="high",
                    title="⚠️ Low Battery Level",
                    message=f"Battery is low at {battery_soc:.1f}%. Consider conserving energy.",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "low"
        elif battery_soc > self.config['BATTERY_LOW_THRESHOLD'] + 5:
            self.last_battery_alert = None

    async def check_grid_alerts(self, grid_power, grid_voltage, grid_status):
        if grid_voltage is None:
            return
        grid_looks_down = abs(grid_power) <= 0.1 and grid_voltage < self.config['GRID_VOLTAGE_THRESHOLD']
        if grid_looks_down:
            self.grid_restore_consecutive_count = 0
            if not self.grid_outage_blocked:
                self.grid_outage_consecutive_count += 1
                if self.grid_outage_consecutive_count == self.config['GRID_OUTAGE_CONSECUTIVE_READINGS']:
                    await self.notification_sender.send(
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
                    self.last_grid_status = False
                    self.grid_outage_blocked = True
            return
        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count += 1
        if self.last_grid_status is False and self.grid_restore_consecutive_count >= self.config['GRID_OUTAGE_CONSECUTIVE_READINGS']:
            await self.notification_sender.send(
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
            self.grid_outage_blocked = False
            self.last_grid_status = True
            self.grid_restore_consecutive_count = 0
        elif self.last_grid_status is None or self.last_grid_status is True:
            self.last_grid_status = True

    async def check_consumption_alerts(self, load_power, now, config):
        from datetime import time
        if time(5, 0) <= now < time(18, 0):
            return
        if time(18, 0) <= now < time(22, 0):
            if load_power > config['EVENING_CONSUMPTION_THRESHOLD']:
                await self.notification_sender.send(
                    category="high_consumption",
                    severity="high",
                    title="📊 High Energy Consumption",
                    message=f"Evening consumption is high at {load_power:.2f} kW (limit {config['EVENING_CONSUMPTION_THRESHOLD']:.0f} kW).",
                    metadata={"load_power": load_power, "limit_kw": config['EVENING_CONSUMPTION_THRESHOLD']}
                )
            return
        if load_power > config['HIGH_CONSUMPTION_THRESHOLD']:
            await self.notification_sender.send(
                category="high_consumption",
                severity="critical",
                title="🚨 Critical Night Consumption",
                message=f"Night consumption is high at {load_power:.2f} kW (limit {config['HIGH_CONSUMPTION_THRESHOLD']:.2f} kW).",
                metadata={"load_power": load_power, "limit_kw": config['HIGH_CONSUMPTION_THRESHOLD']}
            )
