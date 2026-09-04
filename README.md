# Sunsynk Solar Notification System

A lightweight notification system for Sunsynk solar inverters that sends alerts via Telegram when important events occur.

This repository holds two things: the notification system (documented first) and the
[`sunsynk` API client library](#sunsynk-api-client-library) it is built on.

## Features

- 🔋 **Battery Monitoring**: Get alerts when battery levels are low or critical
- ⚡ **Grid Status**: Notifications for grid outages and power restoration, with reminders while the outage lasts
- 📊 **Consumption Tracking**: High energy consumption warnings, with a separate evening threshold
- 📱 **Telegram Notifications**: Send notifications via Telegram bot
- ⏰ **Smart Filtering**: Quiet hours, rate limiting, and severity thresholds
- 🎯 **Simple Setup**: Docker-based deployment with minimal configuration

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Sunsynk account credentials
- Telegram Bot Token (from @BotFather)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sunsynk-api-client.git
cd sunsynk-api-client
```

2. Create the environment file at the repository root (next to `docker-compose.yml`):
```bash
cp zuva/.env.template .env
# Edit .env with your credentials
```

   At a minimum set `SUNSYNK_USERNAME`, `SUNSYNK_PASSWORD` and `ZUVA_API_KEY`.
   The notification API refuses to start without `ZUVA_API_KEY`, and the
   collector must send the same value:
```bash
openssl rand -hex 32   # use the output as ZUVA_API_KEY
```

3. Configure your notification channels:

**For Telegram:**
- Message @BotFather on Telegram
- Create a new bot with `/newbot`
- Copy the bot token to `TELEGRAM_BOT_TOKEN` in .env
- Start a chat with your bot and send `/start`
- Get your chat ID by visiting `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`

4. Start the system:
```bash
docker compose up -d --build
# or, with the same checks and a summary: ./zuva/start.sh
```

Deploying to a server (Portainer) uses
[`scripts/deploy/docker-compose.prod.yml`](scripts/deploy/docker-compose.prod.yml),
which pulls published images instead of building. It fails the deploy with an
explicit message if any required secret is missing from the stack environment.

## Configuration

Every variable the services read is listed in [`zuva/.env.template`](zuva/.env.template).
The ones you are most likely to change:

```bash
# Alert thresholds
BATTERY_LOW_THRESHOLD=20              # Alert when battery below 20%
BATTERY_CRITICAL_THRESHOLD=15         # Critical alert below 15%
HIGH_CONSUMPTION_THRESHOLD_W=400      # Watts, outside the evening window
EVENING_CONSUMPTION_THRESHOLD_W=900   # Watts, 18:00-22:00 local time
POLL_INTERVAL=600                     # Check the inverter every 10 minutes
GRID_OUTAGE_COOLDOWN_MINUTES=30       # Repeat the outage alert every 30 min (0 = once)

# Timezone: containers are UTC by default, which shifts quiet hours and the
# evening consumption window.
TIMEZONE=Africa/Johannesburg

# Sunsynk network resilience
SUNSYNK_REQUEST_TIMEOUT_SECONDS=20
SUNSYNK_CONNECT_TIMEOUT_SECONDS=10
SUNSYNK_MAX_RETRIES=3
SUNSYNK_RETRY_BASE_DELAY_SECONDS=0.5
```

Thresholds are in watts. `HIGH_CONSUMPTION_THRESHOLD` and
`EVENING_CONSUMPTION_THRESHOLD` (without the `_W`) still work but log a
deprecation warning.

## Managing Notification Settings

Every endpoint except `/health` requires the `X-API-Key` header:

```bash
# Update settings for the default user
curl -X POST http://localhost:8001/settings \
  -H "X-API-Key: $ZUVA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "enabled_channels": ["telegram"],
    "telegram_chat_id": "your_chat_id",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "min_severity": "medium",
    "rate_limit_minutes": 15
  }'
```

Settings, alert history and poll readings all live in one SQLite file at
`/data/zuva.db` inside the `zuva-api` container, so keep the `zuva_api_data`
volume across redeploys - that volume is the whole backup. Alerts and readings
older than `HISTORY_RETENTION_DAYS` (90 by default; 0 keeps everything) are
deleted by a periodic sweep inside the API.

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | none | System health check (also the container healthcheck) |
| `POST /settings` | `X-API-Key` | Update notification settings |
| `GET /settings/{user_id}` | `X-API-Key` | Get user settings |
| `POST /alert` | `X-API-Key` | Send an alert (used by the collector, and for testing) |
| `POST /telemetry` | `X-API-Key` | Store one poll's readings (used by the collector) |
| `GET /alerts/history/{user_id}?hours=24` | `X-API-Key` | Get alert history |

`POST /alert` answers 409 when the user has no settings (an alert with nowhere to
go is a configuration error, not a success) and 502 when delivery fails.

## Alert Categories

| Category | Severity | Description |
|----------|----------|-------------|
| `battery_critical` | CRITICAL | Battery below critical threshold |
| `battery_low` | HIGH | Battery below low threshold |
| `grid_outage` | HIGH | Grid power lost |
| `grid_restored` | MEDIUM | Grid power restored |
| `high_consumption` | MEDIUM | Load exceeds threshold |
| `system_error` | HIGH | System errors |
| `sunsynk_login_failure` | CRITICAL | The collector cannot log in to or reach the Sunsynk API |

## Architecture

```
┌─────────────────┐
│  Sunsynk API    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐   alerts    ┌──────────────────┐
│ Alert Monitor   │────────────▶│ Notification API │
│  (Collector)    │  telemetry  │   (FastAPI)      │
└─────────────────┘────────────▶└────┬────────┬────┘
                                     │        │
                                     ▼        ▼
                          ┌──────────────┐  ┌───────────────┐
                          │ SQLite       │  │ Telegram Bot  │
                          │ /data/zuva.db│  └───────────────┘
                          └──────────────┘
```

Sending notifications is the point of the system. Everything else exists to
support that: there is no dashboard and no web frontend, and the stored history
is a record of what was sent, not a product feature.

## Development

Two containers, and only one of them touches storage:

1. **Notification API** (`zuva_api/`): REST API for settings, alerts and telemetry. Owns the single SQLite database.
2. **Alert Monitor** (`zuva/collector/`): Polls the Sunsynk API, evaluates thresholds, and posts alerts and readings to the API. Holds no database credentials.

```bash
./scripts/setup.sh          # create ./venv and install dev dependencies
./run-tests.sh              # full suite with coverage; extra args go to pytest
./run-tests.sh -k grid      # run a subset
./scripts/run-pylint.sh     # pylint over sunsynk, zuva and zuva_api
```

### Running Locally

```bash
./scripts/setup.sh
./venv/bin/pip install -r zuva_api/requirements.txt -r zuva/collector/requirements.txt

# Notification service
ZUVA_API_KEY=dev ./venv/bin/uvicorn zuva_api.main:app --port 8001

# Alert monitor (separate terminal, same key)
ZUVA_API_KEY=dev ./venv/bin/python -m zuva.collector.orchestrator
```

`scripts/manual/` holds two scripts for checking a live system: a Sunsynk login
probe and an end-to-end notification test.

## Troubleshooting

**No notifications received:**
- Check that services are running: `docker compose ps`
- Verify credentials in .env
- Check logs: `docker compose logs -f zuva-api`
- Test the Telegram bot: send `/start` to it
- A 401 from `zuva-api` means the collector's `ZUVA_API_KEY` does not match the API's

**Alert Monitor not connecting:**
- Verify Sunsynk credentials. After a rejected login the collector waits
  `AUTH_FAILURE_BACKOFF_SECONDS` (6h by default) rather than retrying, because
  repeated failed logins make Sunsynk demand a verification code. Restart the
  container once the credentials are fixed.
- Check logs: `docker compose logs -f alert-monitor`
- `docker compose ps` shows the monitor as unhealthy if it has stopped polling:
  the healthcheck reads a heartbeat file that each completed poll touches.

## Network Error Handling

The client handles transient connectivity failures gracefully:

- Retries transient connection/timeout failures with exponential backoff (`SUNSYNK_MAX_RETRIES`, `SUNSYNK_RETRY_BASE_DELAY_SECONDS`)
- Uses configurable connect/request timeouts (`SUNSYNK_CONNECT_TIMEOUT_SECONDS`, `SUNSYNK_REQUEST_TIMEOUT_SECONDS`)
- Raises explicit exceptions:
  - `SunsynkConnectionError` for connection-level failures
  - `SunsynkTimeoutError` for timeout failures
  - `SunsynkApiError` for non-200 API responses on data endpoints

Authentication-related behavior remains unchanged (`InvalidCredentialsException`, `VerificationCodeRequiredException`, `LoginRateLimitedException`).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

# sunsynk API client library

[![CI](https://github.com/jamesridgway/sunsynk-api-client/actions/workflows/ci.yml/badge.svg)](https://github.com/jamesridgway/sunsynk-api-client/actions/workflows/ci.yml)

An API client library for reading data from the Sunsynk API that is used by the Sunsynk Connect apps and
[PowerView](https://pv.inteless.com/) portal.

TLS certificates are verified by default; `verify_tls=False` (or
`SUNSYNK_VERIFY_TLS=false`) disables that for lab use only.

## Example Usage

    import asyncio
    import os

    from sunsynk.client import SunsynkClient


    async def main():
        sunsynk_username = os.getenv('SUNSYNK_USERNAME')
        sunsynk_password = os.getenv('SUNSYNK_PASSWORD')

        async with SunsynkClient(sunsynk_username, sunsynk_password) as client:
            inverters = await client.get_inverters()
            for inverter in inverters:
                grid = await client.get_inverter_realtime_grid(inverter.sn)
                battery = await client.get_inverter_realtime_battery(inverter.sn)
                solar_pv = await client.get_inverter_realtime_input(inverter.sn)

                await client.get_inverter_realtime_output(inverter.sn)

                print(f"Inverter (sn: {inverter.sn}) is drawing {grid.get_power()}W from the grid, "
                      f"{battery.power}W from battery and {solar_pv.get_power()}W from solar.")

        print('Done!')

    asyncio.run(main())
