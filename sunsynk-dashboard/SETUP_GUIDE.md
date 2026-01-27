# 🚀 Quick Setup Guide

Get your Sunsynk notification system running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Sunsynk account credentials
- Telegram account (for Telegram notifications)

## Step 1: Get Telegram Bot Token (Optional)

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Start a chat with your new bot and send `/start`

To get your chat ID:
```bash
# Replace YOUR_BOT_TOKEN with your actual token
curl https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```
Look for `"chat":{"id":123456789}` in the response.

## Step 2: Configure Environment

```bash
cd sunsynk-dashboard

# Copy template
cp .env.template .env

# Edit with your credentials
nano .env  # or use your favorite editor
```

Minimum required settings:
```bash
SUNSYNK_USERNAME=your_email@example.com
SUNSYNK_PASSWORD=your_password

# Notification channel:
TELEGRAM_BOT_TOKEN=123456789:ABC...
```

## Step 3: Start the System

```bash
./start.sh
```

Or manually:
```bash
docker-compose up -d
docker-compose logs -f  # Watch logs
```

## Step 4: Configure User Settings

### Option A: Using curl

```bash
curl -X POST http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "enabled_channels": ["telegram"],
    "telegram_chat_id": "YOUR_CHAT_ID",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "min_severity": "medium",
    "rate_limit_minutes": 15
  }'
```

### Option B: Using Python

```python
import requests

settings = {
    "user_id": "default",
    "enabled_channels": ["telegram"],
    "telegram_chat_id": "123456789",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "min_severity": "medium",
    "rate_limit_minutes": 15
}

response = requests.post("http://localhost:8000/settings", json=settings)
print(response.json())
```

## Step 5: Test Notifications

```bash
# Run test script
python3 test_notifications.py

# Or send manual test
curl -X POST "http://localhost:8000/alert?user_id=default" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "battery_low",
    "severity": "high",
    "title": "Test Alert",
    "message": "Testing notifications!",
    "metadata": {"test": true}
  }'
```

## Step 6: Monitor

```bash
# Check service status
docker-compose ps

# Watch logs
docker-compose logs -f

# Check specific service
docker-compose logs -f alert-monitor
docker-compose logs -f notification-api

# Check API health
curl http://localhost:8000/health
```

## Troubleshooting

### No notifications received

1. **Check service status:**
   ```bash
   docker-compose ps
   # All should be "Up"
   ```

2. **Check logs for errors:**
   ```bash
   docker-compose logs notification-api
   docker-compose logs alert-monitor
   ```

3. **Verify credentials:**
   ```bash
   # Test Telegram bot
   curl https://api.telegram.org/botYOUR_TOKEN/getMe
   
   # Check settings
   curl http://localhost:8000/settings/default
   ```

4. **Send test alert:**
   ```bash
   python3 test_notifications.py
   ```

### Alert monitor not connecting

```bash
# Check Sunsynk credentials
docker-compose logs alert-monitor | grep -i error

# Verify InfluxDB is running
curl http://localhost:8086/health

# Restart services
docker-compose restart alert-monitor
```

### Telegram "Unauthorized" error

- Bot token is incorrect
- Check `.env` file has correct TELEGRAM_BOT_TOKEN
- Restart services: `docker-compose restart`


## Customizing Alert Thresholds

Edit `.env`:

```bash
# Battery alerts
BATTERY_LOW_THRESHOLD=25        # Alert at 25% instead of 20%
BATTERY_CRITICAL_THRESHOLD=15   # Critical at 15% instead of 10%

# Consumption alert
HIGH_CONSUMPTION_THRESHOLD=8    # Alert at 8kW instead of 5kW

# Polling frequency
POLL_INTERVAL=30               # Check every 30 seconds instead of 60
```

Then restart:
```bash
docker-compose restart alert-monitor
```

## Advanced: Multiple Users

Configure settings for different users:

```bash
# User 1
curl -X POST http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{"user_id": "john", "enabled_channels": ["telegram"], "telegram_chat_id": "111111"}'

# User 2  
curl -X POST http://localhost:8000/settings \
  -H "Content-Type: application/json" \
```

Send alerts to specific user:
```bash
curl -X POST "http://localhost:8000/alert?user_id=john" ...
```

## Next Steps

- ✅ System is running and monitoring your inverter
- ✅ Alerts will be sent automatically based on thresholds
- ✅ Check alert history: `curl http://localhost:8000/alerts/history/default?hours=24`

Enjoy your automated solar monitoring! 🌞🔔
