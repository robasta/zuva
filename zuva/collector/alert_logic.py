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
    # Depletion projection. 0 minutes of horizon disables the check entirely.
    'BATTERY_DEPLETION_HORIZON_MINUTES': 120,
    'BATTERY_DEPLETION_URGENT_MINUTES': 60,
    'BATTERY_DEPLETION_CONSECUTIVE_READINGS': 2,
    # Wide enough that a late poll cannot starve the window below the minimum
    # span: at the default 600s interval this holds four or five samples.
    'BATTERY_SOC_WINDOW_MINUTES': 45,
    'BATTERY_DEPLETION_MIN_SPAN_MINUTES': 20,
    'BATTERY_DEPLETION_MIN_RATE_PCT_PER_HOUR': 1.0,
}

STATE_KEYS = (
    'last_battery_alert',
    'last_grid_status',
    'grid_outage_consecutive_count',
    'grid_restore_consecutive_count',
    'grid_outage_blocked',
    'last_grid_outage_alert_at',
    'soc_samples',
    'last_depletion_alert',
    'depletion_consecutive_count',
)

# Depletion alerts escalate and never step back down within one episode.
DEPLETION_STAGES = {'warning': 1, 'urgent': 2}


def format_duration(minutes):
    """Render minutes the way a phone notification should read it."""
    total = int(round(minutes))
    if total < 60:
        return f"{total} min"
    hours, remainder = divmod(total, 60)
    return f"{hours} h" if remainder == 0 else f"{hours} h {remainder} m"


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
        self.soc_samples = []
        self.last_depletion_alert = None
        self.depletion_consecutive_count = 0
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
        # Carrying the SoC window across a restart is the point: rebuilding it
        # from scratch blinds the projection for the whole warm-up span, which
        # is exactly when a restart is most likely (a power cut).
        self.soc_samples = self._parse_soc_samples(self.soc_samples)
        self._prune_soc_samples()

    def _save_state(self):
        if self.state_store is None:
            return
        state = {key: getattr(self, key) for key in STATE_KEYS}
        if isinstance(state['last_grid_outage_alert_at'], datetime):
            state['last_grid_outage_alert_at'] = state['last_grid_outage_alert_at'].isoformat()
        state['soc_samples'] = [[at.isoformat(), soc] for at, soc in state['soc_samples']]
        self.state_store.save(state)

    def _parse_soc_samples(self, value):
        """Rebuild the SoC window from stored JSON, dropping anything unusable."""
        if not isinstance(value, (list, tuple)):
            return []
        samples = []
        for entry in value:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            at = self._parse_timestamp(entry[0])
            if at is None:
                continue
            try:
                samples.append((at, float(entry[1])))
            except (TypeError, ValueError):
                continue
        return samples

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

    # -- discharge rate ----------------------------------------------------

    def record_soc_sample(self, battery_soc, at=None):
        """Add one SoC observation to the rolling window used for projections."""
        if battery_soc is None:
            return
        at = at or local_now()
        self.soc_samples.append((at, float(battery_soc)))
        self._prune_soc_samples(now=at)
        self._save_state()

    def _prune_soc_samples(self, now=None):
        window = timedelta(minutes=float(self._setting('BATTERY_SOC_WINDOW_MINUTES')))
        cutoff = (now or local_now()) - window
        self.soc_samples = [
            (at, soc) for at, soc in sorted(self.soc_samples, key=lambda s: s[0]) if at >= cutoff
        ]

    def soc_discharge_rate(self):
        """Observed discharge over the window in %/hour, or ``None``.

        A SoC slope needs no battery capacity figure and makes no assumption
        about the sign of the reported battery power, and it self-calibrates as
        the pack ages. It is also already net of solar: a battery being topped
        up by the sun simply has no discharge rate.

        ``None`` means "do not project": charging, flat, or a window too narrow
        for the drop to be more than SoC reporting granularity.
        """
        if len(self.soc_samples) < 2:
            return None
        oldest_at, oldest_soc = self.soc_samples[0]
        newest_at, newest_soc = self.soc_samples[-1]
        span_minutes = (newest_at - oldest_at).total_seconds() / 60
        if span_minutes < float(self._setting('BATTERY_DEPLETION_MIN_SPAN_MINUTES')):
            return None
        rate = (oldest_soc - newest_soc) / (span_minutes / 60)
        # A near-zero rate divides out into an absurd horizon, so the floor is
        # what keeps "reaches 20% in 400 hours" out of the projections.
        if rate < float(self._setting('BATTERY_DEPLETION_MIN_RATE_PCT_PER_HOUR')):
            return None
        return rate

    def project_minutes_to(self, battery_soc, target_soc):
        """Minutes until ``battery_soc`` falls to ``target_soc``, or ``None``."""
        rate = self.soc_discharge_rate()
        if rate is None or battery_soc is None or battery_soc <= target_soc:
            return None
        return (battery_soc - target_soc) / rate * 60

    def _projection_clause(self, battery_soc, target_soc, label):
        """A time-to-``label`` sentence for the fixed-threshold alerts.

        Returns ``("", {})`` when there is no usable rate, so those messages stay
        exactly as they were before projections existed.
        """
        minutes = self.project_minutes_to(battery_soc, target_soc)
        if minutes is None:
            return "", {}
        rate = self.soc_discharge_rate()
        clause = f" About {format_duration(minutes)} to {label} at the current {rate:.1f}%/hour."
        return clause, {
            "discharge_rate_pct_per_hour": round(rate, 2),
            "minutes_to_next_threshold": round(minutes),
        }

    # -- battery -----------------------------------------------------------

    async def check_battery_alerts(self, battery_soc):
        critical = self._setting('BATTERY_CRITICAL_THRESHOLD')
        low = self._setting('BATTERY_LOW_THRESHOLD')
        margin = self._setting('BATTERY_RECOVERY_MARGIN')

        if battery_soc <= critical:
            if self.last_battery_alert != "critical":
                clause, projection = self._projection_clause(battery_soc, 0, "empty")
                await self.notification_sender.send(
                    category="battery_critical",
                    severity="critical",
                    title="🚨 Critical Battery Level",
                    message=(
                        f"Battery is critically low at {battery_soc:.1f}%. "
                        f"Immediate attention required!{clause}"
                    ),
                    metadata={"battery_soc": battery_soc, **projection}
                )
                self.last_battery_alert = "critical"
                self._save_state()
        elif battery_soc <= low:
            # Only escalate upward: recovering from critical into the low band is
            # good news and must not raise a fresh alert.
            if self.last_battery_alert is None:
                clause, projection = self._projection_clause(battery_soc, critical, "critical")
                await self.notification_sender.send(
                    category="battery_low",
                    severity="high",
                    title="⚠️ Low Battery Level",
                    message=(
                        f"Battery is low at {battery_soc:.1f}%. "
                        f"Consider conserving energy.{clause}"
                    ),
                    metadata={"battery_soc": battery_soc, **projection}
                )
                self.last_battery_alert = "low"
                self._save_state()
        elif battery_soc > low + margin:
            if self.last_battery_alert is not None:
                self.last_battery_alert = None
                self._save_state()

    async def check_battery_depletion(self, battery_soc):
        """Warn *before* the battery reaches the low threshold, not when it does.

        Fires at most twice per discharge episode: once at ``high`` when the
        projection enters the horizon, then once at ``critical`` when it enters
        the urgent window.
        """
        horizon = float(self._setting('BATTERY_DEPLETION_HORIZON_MINUTES'))
        reserve = float(self._setting('BATTERY_LOW_THRESHOLD'))
        minutes = None if horizon <= 0 else self.project_minutes_to(battery_soc, reserve)

        if minutes is None or minutes > horizon:
            # Nothing to forecast: charging, flat, still warming up, the check is
            # disabled, or already at/below the reserve - where battery_low owns
            # the message and a forecast of the present would just be noise.
            if self.last_depletion_alert is not None or self.depletion_consecutive_count:
                self.last_depletion_alert = None
                self.depletion_consecutive_count = 0
                self._save_state()
            return

        self.depletion_consecutive_count += 1
        if self.depletion_consecutive_count < int(
            self._setting('BATTERY_DEPLETION_CONSECUTIVE_READINGS')
        ):
            self._save_state()
            return

        urgent = minutes <= float(self._setting('BATTERY_DEPLETION_URGENT_MINUTES'))
        stage = 'urgent' if urgent else 'warning'
        if DEPLETION_STAGES[stage] <= DEPLETION_STAGES.get(self.last_depletion_alert, 0):
            return

        rate = self.soc_discharge_rate()
        eta = local_now() + timedelta(minutes=minutes)
        # The severity split is deliberate. zuva-api suppresses anything below
        # critical during quiet hours, which default to 22:00-07:00 and so cover
        # the entire overnight discharge window: a long-horizon warning raised at
        # 23:00 is silent on purpose, and only the urgent one wakes anybody.
        # Forcing critical here would trade one useful message for two.
        await self.notification_sender.send(
            category="battery_depletion",
            severity="critical" if urgent else "high",
            title="🚨 Battery Running Out" if urgent else "⏳ Battery Running Down",
            message=(
                f"Battery at {battery_soc:.1f}% and falling {rate:.1f}%/hour. "
                f"Reaches {reserve:.0f}% at about {eta.strftime('%H:%M')} "
                f"(in {format_duration(minutes)})."
            ),
            metadata={
                "battery_soc": battery_soc,
                "discharge_rate_pct_per_hour": round(rate, 2),
                "reserve_soc": reserve,
                "minutes_to_reserve": round(minutes),
                "projected_at": eta.isoformat(),
                "consecutive_readings": self.depletion_consecutive_count,
            },
        )
        self.last_depletion_alert = stage
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
