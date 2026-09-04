"""Alert evaluation: pure decision logic over one reading at a time.

Consumption values are handled in **watts**, matching what the inverter output
endpoint reports (``output.pac``). Threshold config is named ``*_W`` so the unit
is unambiguous at the call site.

Suppression state (what has already been alerted, grid up/down, cooldown
clocks) is optionally persisted through a ``StateStore`` so a restart does not
re-alert conditions the user has already been told about.
"""
import logging
from datetime import datetime, timedelta

from .timeutil import get_timezone, local_now

# Fallbacks so a partial config can never KeyError mid-poll.
DEFAULTS = {
    'BATTERY_LOW_THRESHOLD': 20.0,
    'BATTERY_CRITICAL_THRESHOLD': 10.0,
    'BATTERY_RECOVERY_MARGIN': 5.0,
    'HIGH_CONSUMPTION_THRESHOLD_W': 400.0,
    'EVENING_CONSUMPTION_THRESHOLD_W': 900.0,
    'GRID_OUTAGE_CONSECUTIVE_READINGS': 3,
    'GRID_VOLTAGE_THRESHOLD': 50.0,
    'GRID_OUTAGE_COOLDOWN_MINUTES': 30,
    'DAYTIME_START_HOUR': 5,
    'DAYTIME_END_HOUR': 18,
    'EVENING_END_HOUR': 22,
}

STATE_KEYS = (
    'last_battery_alert',
    'last_grid_status',
    'grid_outage_consecutive_count',
    'grid_restore_consecutive_count',
    'grid_outage_blocked',
    'last_grid_outage_alert_at',
)


class AlertEvaluator:
    def __init__(self, config, notification_sender, state_store=None):
        self.config = config or {}
        self.notification_sender = notification_sender
        self.state_store = state_store
        self.logger = logging.getLogger(__name__)
        self.last_battery_alert = None
        self.last_grid_status = None
        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count = 0
        self.grid_outage_blocked = False
        self.last_grid_outage_alert_at = None
        if self.state_store is not None:
            self._load_state()

    def _setting(self, key):
        value = self.config.get(key)
        return DEFAULTS[key] if value is None else value

    # -- state persistence -------------------------------------------------

    def _load_state(self):
        state = self.state_store.load()
        for key in STATE_KEYS:
            if key in state:
                setattr(self, key, state[key])
        self.last_grid_outage_alert_at = self._parse_timestamp(self.last_grid_outage_alert_at)

    def _save_state(self):
        if self.state_store is None:
            return
        state = {key: getattr(self, key) for key in STATE_KEYS}
        if isinstance(state['last_grid_outage_alert_at'], datetime):
            state['last_grid_outage_alert_at'] = state['last_grid_outage_alert_at'].isoformat()
        self.state_store.save(state)

    @staticmethod
    def _parse_timestamp(value):
        if value is None or isinstance(value, datetime):
            return value
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=get_timezone())
        return parsed

    # -- battery -----------------------------------------------------------

    async def check_battery_alerts(self, battery_soc):
        critical = self._setting('BATTERY_CRITICAL_THRESHOLD')
        low = self._setting('BATTERY_LOW_THRESHOLD')
        margin = self._setting('BATTERY_RECOVERY_MARGIN')

        if battery_soc <= critical:
            if self.last_battery_alert != "critical":
                await self.notification_sender.send(
                    category="battery_critical",
                    severity="critical",
                    title="🚨 Critical Battery Level",
                    message=f"Battery is critically low at {battery_soc:.1f}%. Immediate attention required!",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "critical"
                self._save_state()
        elif battery_soc <= low:
            # Only escalate upward: recovering from critical into the low band is
            # good news and must not raise a fresh alert.
            if self.last_battery_alert is None:
                await self.notification_sender.send(
                    category="battery_low",
                    severity="high",
                    title="⚠️ Low Battery Level",
                    message=f"Battery is low at {battery_soc:.1f}%. Consider conserving energy.",
                    metadata={"battery_soc": battery_soc}
                )
                self.last_battery_alert = "low"
                self._save_state()
        elif battery_soc > low + margin:
            if self.last_battery_alert is not None:
                self.last_battery_alert = None
                self._save_state()

    # -- grid --------------------------------------------------------------

    async def check_grid_alerts(self, grid_power, grid_voltage, grid_status):
        if grid_voltage is None:
            return
        required = self._setting('GRID_OUTAGE_CONSECUTIVE_READINGS')
        grid_looks_down = abs(grid_power) <= 0.1 and grid_voltage < self._setting('GRID_VOLTAGE_THRESHOLD')

        if grid_looks_down:
            self.grid_restore_consecutive_count = 0
            if not self.grid_outage_blocked:
                self.grid_outage_consecutive_count += 1
                if self.grid_outage_consecutive_count == required:
                    await self._send_grid_outage(grid_power, grid_voltage, grid_status, reminder=False)
            else:
                await self._maybe_remind_grid_outage(grid_power, grid_voltage, grid_status)
            self._save_state()
            return

        self.grid_outage_consecutive_count = 0
        self.grid_restore_consecutive_count += 1
        if self.last_grid_status is False and self.grid_restore_consecutive_count >= required:
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
            self.last_grid_outage_alert_at = None
        elif self.last_grid_status is None or self.last_grid_status is True:
            self.last_grid_status = True
        self._save_state()

    async def _send_grid_outage(self, grid_power, grid_voltage, grid_status, reminder, minutes_down=None):
        if reminder:
            title = "⚡ Grid Still Offline"
            message = (
                f"The grid has been offline for about {minutes_down:.0f} minutes. "
                "Your system is still running on battery power."
            )
        else:
            title = "⚡ Grid Outage Detected"
            message = "The grid has gone offline. Your system is now running on battery power."

        metadata = {
            "grid_power": grid_power,
            "grid_voltage": grid_voltage,
            "grid_status": grid_status,
            "consecutive_readings": self.grid_outage_consecutive_count,
            "reminder": reminder,
        }
        if minutes_down is not None:
            metadata["minutes_offline"] = round(minutes_down)

        await self.notification_sender.send(
            category="grid_outage",
            severity="high",
            title=title,
            message=message,
            metadata=metadata,
        )
        self.last_grid_status = False
        self.grid_outage_blocked = True
        self.last_grid_outage_alert_at = local_now()

    async def _maybe_remind_grid_outage(self, grid_power, grid_voltage, grid_status):
        """Re-alert during a sustained outage, no more often than the cooldown."""
        cooldown_minutes = self._setting('GRID_OUTAGE_COOLDOWN_MINUTES')
        if not cooldown_minutes or cooldown_minutes <= 0:
            return
        last_alert = self._parse_timestamp(self.last_grid_outage_alert_at)
        if last_alert is None:
            return
        elapsed = local_now() - last_alert
        if elapsed < timedelta(minutes=cooldown_minutes):
            return
        await self._send_grid_outage(
            grid_power,
            grid_voltage,
            grid_status,
            reminder=True,
            minutes_down=elapsed.total_seconds() / 60,
        )

    # -- consumption -------------------------------------------------------

    async def check_consumption_alerts(self, load_power_w, now=None, config=None):
        """Alert on load outside daylight hours.

        ``now`` is a local ``time``; it defaults to the configured timezone so
        callers cannot accidentally evaluate business hours against UTC.
        """
        if config is not None:
            self.config = config
        if now is None:
            now = local_now().time()

        day_start = int(self._setting('DAYTIME_START_HOUR'))
        day_end = int(self._setting('DAYTIME_END_HOUR'))
        evening_end = int(self._setting('EVENING_END_HOUR'))
        hour = now.hour

        if day_start <= hour < day_end:
            return

        if day_end <= hour < evening_end:
            limit = self._setting('EVENING_CONSUMPTION_THRESHOLD_W')
            if load_power_w > limit:
                await self.notification_sender.send(
                    category="high_consumption",
                    severity="high",
                    title="📊 High Energy Consumption",
                    message=(
                        f"Evening consumption is high at {load_power_w:.0f} W "
                        f"(limit {limit:.0f} W)."
                    ),
                    metadata={"load_power_w": load_power_w, "limit_w": limit}
                )
            return

        limit = self._setting('HIGH_CONSUMPTION_THRESHOLD_W')
        if load_power_w > limit:
            await self.notification_sender.send(
                category="high_consumption",
                severity="critical",
                title="🚨 Critical Night Consumption",
                message=(
                    f"Night consumption is high at {load_power_w:.0f} W "
                    f"(limit {limit:.0f} W)."
                ),
                metadata={"load_power_w": load_power_w, "limit_w": limit}
            )
