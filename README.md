# Sunsynk Solar Notification System

A lightweight notification system for Sunsynk solar inverters that sends alerts via Telegram when important events occur.

## Features

- 🔋 **Battery Monitoring**: Get alerts when battery levels are low or critical
- ⚡ **Grid Status**: Notifications for grid outages and power restoration  
- 📊 **Consumption Tracking**: High energy consumption warnings
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
cd sunsynk-api-client/zuva
```

2. Create environment file:
```bash
cp .env.template .env
# Edit .env with your credentials
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
docker compose --env-file .env -f ../docker-compose.yml up -d
```

## Configuration

Edit the `.env` file to customize:

```bash
# Alert Thresholds
BATTERY_LOW_THRESHOLD=20        # Alert when battery below 20%
BATTERY_CRITICAL_THRESHOLD=10   # Critical alert below 10%
HIGH_CONSUMPTION_THRESHOLD=5    # Alert when load exceeds 5 kW
POLL_INTERVAL=60               # Check inverter every 60 seconds
```

## Managing Notification Settings

Use the API to configure your notification preferences:

```bash
# Update settings for default user
curl -X POST http://localhost:8000/settings \
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

## API Endpoints

- `GET /health` - System health check
- `POST /settings` - Update notification settings
- `GET /settings/{user_id}` - Get user settings
- `POST /alert` - Send manual alert (for testing)
- `GET /alerts/history/{user_id}?hours=24` - Get alert history

## Alert Categories

| Category | Severity | Description |
|----------|----------|-------------|
| `battery_critical` | CRITICAL | Battery below critical threshold |
| `battery_low` | HIGH | Battery below low threshold |
| `grid_outage` | HIGH | Grid power lost |
| `grid_restored` | MEDIUM | Grid power restored |
| `high_consumption` | MEDIUM | Load exceeds threshold |
| `system_error` | HIGH | System errors |

## Architecture

```
┌─────────────────┐
│  Sunsynk API    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Alert Monitor   │─────▶│ Notification API │
│  (Collector)    │      │   (FastAPI)      │
└─────────────────┘      └────────┬─────────┘
         │                        │
         ▼                        ▼
    ┌─────────┐         ┌─────────────────┐
    │ InfluxDB│         │  Telegram Bot   │
    │         │         │  Telegram Bot  │
    └─────────┘         └─────────────────┘
```

## Development

The system consists of three main components:

1. **InfluxDB**: Stores alert history and user settings
2. **Notification API**: REST API for managing settings and sending notifications
3. **Alert Monitor**: Polls Sunsynk API and triggers alerts based on thresholds

### Running Locally

```bash
# Install Python dependencies
pip install -r zuva_api/requirements.txt
cd zuva
pip install -r collector/requirements.txt

# Run notification service
cd ..
python -m zuva_api.main

# Run alert monitor (in separate terminal)
cd zuva
python -m collector.alert_monitor
```

## Troubleshooting

**No notifications received:**
- Check that services are running: `docker compose --env-file zuva/.env -f docker-compose.yml ps`
- Verify credentials in .env file
- Check logs: `docker compose --env-file zuva/.env -f docker-compose.yml logs -f zuva-api`
- Test Telegram bot: Send `/start` to your bot

**Alert Monitor not connecting:**
- Verify Sunsynk credentials
- Check logs: `docker compose --env-file zuva/.env -f docker-compose.yml logs -f alert-monitor`
- Ensure InfluxDB is running: `curl http://localhost:8086/health`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
[![CI](https://github.com/jamesridgway/sunsynk-api-client/actions/workflows/ci.yml/badge.svg)](https://github.com/jamesridgway/sunsynk-api-client/actions/workflows/ci.yml)

An API client library for reading data from the Sunsynk API that is used by the Sunsynk Connect apps and 
[PowerView](https://pv.inteless.com/) portal.


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
    
                print(f"Inverter (sn: {inverter.sn}) is drawing {grid.get_power()}kWh from the grid, {battery.power}kWh from battery and {solar_pv.get_power()}kWh.")
    
        print('Done!')
    
    asyncio.run(main())
