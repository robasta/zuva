"""Alert Orchestrator for Sunsynk Inverter.

Coordinates telemetry, alert logic, and notification.
"""
import asyncio
import logging
import os

# The image puts the sunsynk package on PYTHONPATH (see Dockerfile), so no
# sys.path manipulation is needed here.
from sunsynk.client import (
    InvalidCredentialsException,
    LoginRateLimitedException,
    SunsynkApiError,
    SunsynkClient,
    SunsynkConnectionError,
    SunsynkTimeoutError,
    VerificationCodeRequiredException,
)
from sunsynk.resource import to_float

from . import heartbeat
from .alert_logic import AlertEvaluator
from .notification import NotificationSender
from .state_store import StateStore
from .telemetry import TelemetryCollector
from .timeutil import local_now

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARN").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARN))
logger = logging.getLogger(__name__)

# Configuration
SUNSYNK_USERNAME = os.getenv("SUNSYNK_USERNAME")
SUNSYNK_PASSWORD = os.getenv("SUNSYNK_PASSWORD")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
LOGIN_RETRY_WAIT_SECONDS = int(os.getenv("LOGIN_RETRY_WAIT_SECONDS", "900"))
# Bad credentials do not heal on their own, and repeated failed logins are what
# makes Sunsynk demand a verification code. Back off hard instead of hammering.
AUTH_FAILURE_BACKOFF_SECONDS = int(os.getenv("AUTH_FAILURE_BACKOFF_SECONDS", "21600"))

NOTIFICATION_API_URL = os.getenv("NOTIFICATION_API_URL", "http://zuva-api:8001")
ZUVA_API_KEY = os.getenv("ZUVA_API_KEY")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")

AUTH_ERRORS = (InvalidCredentialsException, VerificationCodeRequiredException)
TRANSIENT_ERRORS = (
    SunsynkTimeoutError,
    SunsynkConnectionError,
    SunsynkApiError,
    LoginRateLimitedException,
)


def _threshold_watts(name, legacy_name, default):
    """Read a watt threshold, accepting the pre-rename env var name.

    Legacy values were already compared against watts, so they are carried over
    unchanged - only the name gains its unit.
    """
    raw = os.getenv(name)
    if raw is not None:
        return float(raw)
    legacy = os.getenv(legacy_name)
    if legacy is not None:
        logger.warning("%s is deprecated, use %s instead (value is in watts)", legacy_name, name)
        return float(legacy)
    return default


# Alert Thresholds config dict for injection
ALERT_CONFIG = {
    'BATTERY_LOW_THRESHOLD': float(os.getenv("BATTERY_LOW_THRESHOLD", "20")),
    'BATTERY_CRITICAL_THRESHOLD': float(os.getenv("BATTERY_CRITICAL_THRESHOLD", "10")),
    'HIGH_CONSUMPTION_THRESHOLD_W': _threshold_watts(
        "HIGH_CONSUMPTION_THRESHOLD_W", "HIGH_CONSUMPTION_THRESHOLD", 400.0
    ),
    'EVENING_CONSUMPTION_THRESHOLD_W': _threshold_watts(
        "EVENING_CONSUMPTION_THRESHOLD_W", "EVENING_CONSUMPTION_THRESHOLD", 900.0
    ),
    'GRID_OUTAGE_CONSECUTIVE_READINGS': int(os.getenv("GRID_OUTAGE_CONSECUTIVE_READINGS", "3")),
    'GRID_VOLTAGE_THRESHOLD': float(os.getenv("GRID_VOLTAGE_THRESHOLD", "50.0")),
    'GRID_OUTAGE_COOLDOWN_MINUTES': int(os.getenv("GRID_OUTAGE_COOLDOWN_MINUTES", "30")),
}


class AlertOrchestrator:
    def __init__(self):
        # One HTTP client to zuva-api for both alerts and telemetry: the API owns
        # the database, so the collector needs no storage credentials at all.
        self.notification = NotificationSender(
            NOTIFICATION_API_URL, DEFAULT_USER_ID, api_key=ZUVA_API_KEY
        )
        self.telemetry = TelemetryCollector(self.notification)
        self.alerter = AlertEvaluator(ALERT_CONFIG, self.notification, state_store=StateStore())

    async def connect_client_with_retry(self):
        """Log in, returning ``(client, retry_wait_seconds)``.

        On success the wait is 0. On failure the client is None and the caller
        should sleep for the returned number of seconds: a short wait for
        transient connectivity problems, a long one for credential problems.
        """
        for attempt in (1, 2):
            client = SunsynkClient(SUNSYNK_USERNAME, SUNSYNK_PASSWORD)
            try:
                await client.login()
                logger.info("Connected to Sunsynk API")
                return client, 0
            except AUTH_ERRORS as error:
                await client.close()
                logger.critical("Sunsynk authentication failed: %s", error)
                await self._notify_login_failure(
                    title="🚨 Sunsynk Authentication Failed",
                    message=(
                        "Sunsynk rejected the configured credentials. "
                        "Monitoring is paused until this is fixed. "
                        f"Error: {error}."
                    ),
                    attempts=attempt,
                    wait_seconds=AUTH_FAILURE_BACKOFF_SECONDS,
                    error=error,
                )
                # Do not retry: a second attempt fails identically and pushes the
                # account towards a verification-code lockout.
                return None, AUTH_FAILURE_BACKOFF_SECONDS
            except TRANSIENT_ERRORS as error:
                await client.close()
                if attempt == 1:
                    logger.warning(
                        "Sunsynk connectivity attempt 1 failed: %s. Retrying in %s seconds.",
                        error,
                        LOGIN_RETRY_WAIT_SECONDS,
                    )
                    await asyncio.sleep(LOGIN_RETRY_WAIT_SECONDS)
                    continue
                logger.critical("Sunsynk connectivity attempt 2 failed: %s", error)
                await self._notify_login_failure(
                    title="🚨 Sunsynk Connectivity Failed Twice",
                    message=(
                        "Unable to reach Sunsynk API after retry. "
                        f"Second failure: {error}."
                    ),
                    attempts=attempt,
                    wait_seconds=LOGIN_RETRY_WAIT_SECONDS,
                    error=error,
                )
                return None, LOGIN_RETRY_WAIT_SECONDS
            except Exception as error:  # pylint: disable=broad-except
                await client.close()
                if attempt == 1:
                    logger.warning(
                        "Sunsynk login attempt 1 failed: %s. Retrying in %s seconds.",
                        error,
                        LOGIN_RETRY_WAIT_SECONDS,
                    )
                    await asyncio.sleep(LOGIN_RETRY_WAIT_SECONDS)
                    continue
                logger.critical("Sunsynk login attempt 2 failed: %s", error)
                await self._notify_login_failure(
                    title="🚨 Sunsynk Login Failed Twice",
                    message=(
                        "Sunsynk login failed after retry. "
                        f"Second failure: {error}."
                    ),
                    attempts=attempt,
                    wait_seconds=LOGIN_RETRY_WAIT_SECONDS,
                    error=error,
                )
                return None, LOGIN_RETRY_WAIT_SECONDS
        return None, LOGIN_RETRY_WAIT_SECONDS

    async def _notify_login_failure(self, *, title, message, attempts, wait_seconds, error):
        await self.notification.send(
            category="sunsynk_login_failure",
            severity="critical",
            title=title,
            message=message,
            metadata={
                "attempts": attempts,
                "retry_wait_seconds": wait_seconds,
                "error": str(error),
            },
        )

    async def poll_once(self, client):
        """Read one sample, store it, and evaluate alerts."""
        plants = await client.get_plants()
        if not plants:
            logger.warning("No plants found")
            return
        inverters = await client.get_inverters()
        if not inverters:
            logger.warning("No inverters found")
            return

        # Single-site deployment: the first plant/inverter is the only one.
        # Multi-inverter support would loop here and tag telemetry per inverter.
        inverter = inverters[0]
        plant_id = plants[0].id

        battery = await client.get_inverter_realtime_battery(inverter.sn)
        grid = await client.get_inverter_realtime_grid(inverter.sn)
        output = await client.get_inverter_realtime_output(inverter.sn)
        input_data = await client.get_inverter_realtime_input(inverter.sn)

        # All power values below are watts, as reported by the inverter.
        battery_soc = to_float(getattr(battery, 'soc', None), 0.0)
        grid_power_w = to_float(grid.get_power() if hasattr(grid, 'get_power') else None, 0.0)
        grid_voltage = to_float(grid.get_voltage() if hasattr(grid, 'get_voltage') else None)
        grid_status = getattr(grid, 'status', None)
        load_power_w = to_float(getattr(output, 'pac', None), 0.0)
        battery_power_w = to_float(getattr(battery, 'power', None))
        battery_voltage = to_float(battery.get_voltage() if hasattr(battery, 'get_voltage') else None)
        input_power_w = to_float(
            input_data.get_power() if hasattr(input_data, 'get_power') else None, 0.0
        )

        logger.info(
            "Battery: %s%%, Grid: %sW, Load: %sW, Solar: %sW",
            battery_soc, grid_power_w, load_power_w, input_power_w,
        )

        await self.telemetry.write(
            inverter_sn=inverter.sn,
            plant_id=plant_id,
            load_power_w=load_power_w,
            grid_power_w=grid_power_w,
            battery_soc=battery_soc,
            grid_voltage=grid_voltage,
            grid_status=grid_status,
            battery_power_w=battery_power_w,
            battery_voltage=battery_voltage,
            input_power_w=input_power_w,
        )

        await self.alerter.check_battery_alerts(battery_soc)
        await self.alerter.check_grid_alerts(grid_power_w, grid_voltage, grid_status)
        await self.alerter.check_consumption_alerts(load_power_w, local_now().time())
        heartbeat.touch()

    async def monitor_loop(self):
        if not SUNSYNK_USERNAME or not SUNSYNK_PASSWORD:
            logger.error("SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set")
            return
        while True:
            client, retry_wait = await self.connect_client_with_retry()
            if client is None:
                logger.warning("Sunsynk login unavailable, retrying in %s seconds", retry_wait)
                await asyncio.sleep(retry_wait)
                continue
            try:
                while True:
                    try:
                        await self.poll_once(client)
                    except AUTH_ERRORS as auth_error:
                        logger.error("Authentication error in monitoring loop: %s", auth_error)
                        break
                    except LoginRateLimitedException as rate_error:
                        logger.warning("Login rate limited in monitoring loop: %s", rate_error)
                    except (SunsynkTimeoutError, SunsynkConnectionError, SunsynkApiError) as network_error:
                        logger.warning(
                            "Connectivity error in monitoring loop: %s", network_error, exc_info=True
                        )
                    except Exception as error:  # pylint: disable=broad-except
                        logger.error("Error in monitoring loop: %s", error, exc_info=True)
                    await asyncio.sleep(POLL_INTERVAL)
            finally:
                await client.close()

    async def shutdown(self):
        await self.notification.aclose()


async def main():
    orchestrator = AlertOrchestrator()
    try:
        await orchestrator.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
