# Sunsynk Solar Dashboard & Notification Architecture

## Overview
This document outlines the architecture for extending the Sunsynk API client into a comprehensive solar monitoring system with real-time dashboards, intelligent notifications, and mobile integration running on a Raspberry Pi.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Sunsynk API   │◄──►│  Raspberry Pi    │◄──►│  Mobile App     │
│   (External)    │    │  Data Collector  │    │  Dashboard      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
┌─────────────────┐            ▼                          │
│  Weather API    │◄─── ┌──────────────────┐              │
│ (OpenWeather/   │     │ Local Database   │              │
│  WeatherStack)  │     │ (InfluxDB/SQLite)│              │
└─────────────────┘     └──────────────────┘              │
                              │                          │
                              ▼                          │
                       ┌──────────────────┐              │
                       │ Analytics Engine │              │
                       │ (Consumption/    │              │
                       │  Prediction AI)  │              │
                       └──────────────────┘              │
                              │                          │
                              ▼                          │
                       ┌──────────────────┐              │
                       │ Dashboard Server │              │
                       │ (FastAPI/Grafana)│              │
                       └──────────────────┘              │
                              │                          │
                              ▼                          │
                    ┌──────────────────────┐             │
                    │ Notification Engine  │◄────────────┘
                    │ (WhatsApp/SMS/Call)  │
                    └──────────────────────┘
```

## Core Components

### 1. Data Collection Service (Raspberry Pi)

**File Structure:**
```
sunsynk-dashboard/
├── collector/
│   ├── __init__.py
│   ├── data_collector.py      # Main collection service
│   ├── weather_collector.py   # Weather data collection
│   ├── database.py            # Database abstraction
│   └── models.py              # Extended data models
├── analytics/
│   ├── __init__.py
│   ├── consumption_analyzer.py # Consumption pattern analysis
│   ├── battery_predictor.py   # Battery usage predictions
│   ├── weather_analyzer.py    # Weather correlation analysis
│   └── usage_optimizer.py     # Usage optimization recommendations
├── dashboard/
│   ├── __init__.py
│   ├── api.py                 # FastAPI web server
│   ├── websockets.py          # Real-time updates
│   └── templates/             # Web dashboard templates
├── notifications/
│   ├── __init__.py
│   ├── alert_engine.py        # Rule-based alerting
│   ├── channels/              # Notification channels
│   │   ├── whatsapp.py
│   │   ├── sms.py
│   │   ├── voice_call.py      # Voice call alerts
│   │   └── push.py
├── mobile/                    # React Native/Flutter app
├── config/
│   ├── alerts.yaml            # Alert configuration
│   └── dashboard.yaml         # Dashboard configuration
└── docker-compose.yml         # Complete stack deployment
```

**Key Features:**
- **Historical Analytics** - Trend analysis and performance optimization
- **Offline Capability** - Mobile app works even when connectivity is poor

### 2. Database Layer

**Recommended: InfluxDB** (Time-series optimized)
```python
# Example data schema
measurement_schema = {
    "solar_metrics": {
        "time": "timestamp",
        "tags": {
            "inverter_sn": "string",
            "plant_id": "string"
        },
        "fields": {
            "grid_power": "float",           # kW from/to grid
            "battery_power": "float",        # kW from/to battery
            "solar_power": "float",          # kW from solar
            "battery_soc": "float",          # % state of charge
            "grid_voltage": "float",         # V
            "load_power": "float",           # kW consumed by loads
            "daily_generation": "float",     # kWh today
            "daily_consumption": "float",    # kWh today
            "hourly_consumption": "float",   # kWh this hour
            "efficiency": "float"            # %
        }
    },
    "weather_data": {
        "time": "timestamp",
        "tags": {
            "location": "string"
        },
        "fields": {
            "temperature": "float",          # °C
            "humidity": "float",             # %
            "cloud_cover": "float",          # %
            "uv_index": "float",             # UV index
            "sunshine_hours": "float",       # hours projected
            "solar_irradiance": "float",     # W/m²
            "weather_condition": "string"    # sunny/cloudy/rain
        }
    },
    "consumption_analysis": {
        "time": "timestamp",
        "tags": {
            "analysis_type": "string"        # hourly/daily/monthly
        },
        "fields": {
            "avg_consumption": "float",      # kW average
            "peak_consumption": "float",     # kW peak
            "battery_depletion_rate": "float", # %/hour
            "projected_runtime": "float",    # hours until 15%
            "geyser_runtime_available": "float" # minutes at current SOC
        }
    }
}
```

**Alternative: SQLite** (Simpler setup)
```sql
CREATE TABLE solar_readings (
    timestamp DATETIME PRIMARY KEY,
    inverter_sn TEXT,
    grid_power REAL,
    battery_power REAL,
    solar_power REAL,
    battery_soc REAL,
    -- ... other metrics
);
```

### 3. Dashboard Server (FastAPI + WebSockets)

**Real-time Web Dashboard:**
```python
# dashboard/api.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import asyncio

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Send real-time solar data
        data = await get_latest_solar_data()
        await websocket.send_json(data)
        await asyncio.sleep(5)

@app.get("/api/metrics/current")
async def get_current_metrics():
    return await get_latest_solar_data()

@app.get("/api/metrics/history")
async def get_historical_data(hours: int = 24):
    return await get_historical_solar_data(hours)
```

**Dashboard Features:**
- **Real-time Gauges**: Current power flow, battery level, grid status, load consumption
- **Consumption Analytics**:
  - Hourly consumption graphs with 15-minute granularity
  - Daily consumption trends with peak usage identification
  - Monthly consumption patterns with seasonal analysis
- **Weather Integration**:
  - Current weather conditions with solar irradiance
  - Next-hour sunshine projection
  - Daily sunshine hours forecast
  - Weather-based generation predictions
- **Battery Intelligence**:
  - Current usage vs generation analysis
  - Projected battery runtime at current consumption
  - Geyser runtime calculator (time available without dropping below 15%)
  - Historical usage pattern analysis
- **Smart Alerts Dashboard**: Configure time-based and conditional alerts
- **Efficiency Metrics**: kWh/kWp ratio, self-consumption percentage
- **Financial Dashboard**: Cost savings, grid import/export costs

### 4. Notification Engine

**Alert Rules Configuration (`config/alerts.yaml`):**
```yaml
alerts:
  # Battery status alerts
  battery_full:
    condition: "battery_soc >= 100"
    severity: "info"
    cooldown: "6h"
    channels: ["push"]
    message: "Battery fully charged: {battery_soc}%"
  
  battery_low_daytime:
    condition: "battery_soc < 65 AND hour >= 11 AND hour <= 18"
    severity: "warning"
    cooldown: "1h"
    channels: ["whatsapp", "push"]
    message: "Battery low during peak hours: {battery_soc}% at {time}"
  
  battery_critical_high_usage:
    condition: "battery_soc <= 15 AND load_power > 0.4"
    severity: "critical"
    cooldown: "5min"
    channels: ["voice_call", "sms", "whatsapp"]
    message: "URGENT: Battery critical {battery_soc}% with high usage {load_power}kW"
  
  # Weather-based alerts
  low_sunshine_projected:
    condition: "sunshine_hours_today < 4"
    severity: "warning"
    cooldown: "24h"
    time_check: "06:00"
    channels: ["push"]
    message: "Low sunshine projected today: {sunshine_hours_today} hours"
  
  continuous_low_sunshine:
    condition: "solar_irradiance < 200 AND duration > 2h"
    severity: "warning"
    cooldown: "4h"
    channels: ["whatsapp"]
    message: "Low sunshine for {duration}: {solar_irradiance}W/m²"
  
  # Consumption alerts
  high_consumption_threshold:
    condition: "load_power > user_defined_threshold"
    severity: "warning"
    cooldown: "30min"
    channels: ["push"]
    message: "High consumption: {load_power}kW (threshold: {threshold}kW)"
  
  battery_depletion_risk:
    condition: "projected_runtime < 2h AND battery_soc > 15"
    severity: "warning"
    cooldown: "1h"
    channels: ["whatsapp", "push"]
    message: "Battery may deplete in {projected_runtime}h at current usage"
  
  # System alerts
  grid_outage:
    condition: "grid_power == 0 AND time_range > 5min"
    severity: "critical"
    cooldown: "15min"
    channels: ["sms", "whatsapp", "voice_call"]
    message: "Grid outage detected for {duration}"
  
  inverter_offline:
    condition: "last_update > 10min"
    severity: "critical"
    cooldown: "30min"
    channels: ["sms", "whatsapp"]
    message: "Inverter {inverter_sn} appears offline"
```

**Notification Channels:**

**WhatsApp Integration:**
```python
# notifications/channels/whatsapp.py
from twilio.rest import Client

class WhatsAppNotifier:
    def __init__(self, account_sid, auth_token, from_number):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
    
    async def send_message(self, to_number, message):
        self.client.messages.create(
            body=message,
            from_=f'whatsapp:{self.from_number}',
            to=f'whatsapp:{to_number}'
        )
```

**SMS Integration:**
```python
# notifications/channels/sms.py
from twilio.rest import Client

class SMSNotifier:
    async def send_sms(self, to_number, message):
        # Twilio, AWS SNS, or local GSM module integration
        pass
```

**Push Notifications:**
```python
# notifications/channels/push.py
from pyfcm import FCMNotification

class PushNotifier:
    def __init__(self, api_key):
        self.push_service = FCMNotification(api_key=api_key)
    
    async def send_push(self, registration_id, title, message):
        self.push_service.notify_single_device(
            registration_id=registration_id,
            message_title=title,
            message_body=message
        )
```

**Voice Call Integration:**
```python
# notifications/channels/voice_call.py
from twilio.rest import Client
from twilio.twiml import VoiceResponse

class VoiceCallNotifier:
    def __init__(self, account_sid, auth_token, from_number):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
    
    async def make_alert_call(self, to_number, message):
        # Create TwiML for voice message
        response = VoiceResponse()
        response.say(f"Solar system alert: {message}", voice='alice')
        response.pause(length=2)
        response.say("Press any key to acknowledge", voice='alice')
        
        call = self.client.calls.create(
            twiml=str(response),
            to=to_number,
            from_=self.from_number
        )
        return call.sid
```

**Weather Data Integration:**
```python
# collector/weather_collector.py
import aiohttp
from datetime import datetime, timedelta

class WeatherCollector:
    def __init__(self, api_key, location):
        self.api_key = api_key
        self.location = location
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    async def get_current_weather(self):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/weather"
            params = {
                'q': self.location,
                'appid': self.api_key,
                'units': 'metric'
            }
            async with session.get(url, params=params) as response:
                data = await response.json()
                return {
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'cloud_cover': data['clouds']['all'],
                    'uv_index': await self._get_uv_index(),
                    'weather_condition': data['weather'][0]['main'].lower()
                }
    
    async def get_hourly_forecast(self):
        # Get next hour sunshine projection
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/forecast"
            params = {
                'q': self.location,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': 8  # Next 24 hours (3-hour intervals)
            }
            async with session.get(url, params=params) as response:
                data = await response.json()
                return self._calculate_sunshine_hours(data['list'])
```

### 5. Mobile Application

**Technology Options:**
1. **React Native** (Cross-platform, web skills)
2. **Flutter** (High performance, single codebase)
3. **Progressive Web App** (No app store, instant updates)

**Core Features:**
- **Live Dashboard**: Real-time power flow diagram with current consumption
- **Consumption Analytics**:
  - Daily consumption graphs with hourly breakdown
  - Hourly consumption trends (15-minute intervals)
  - Monthly consumption patterns and comparisons
- **Battery Intelligence**:
  - Current battery runtime projection
  - Geyser usage calculator ("Can I run geyser for X minutes?")
  - Load-specific runtime estimates
  - Battery depletion rate analysis
- **Weather Integration**:
  - Current weather conditions and solar irradiance
  - Hourly sunshine forecast
  - Daily sunshine hours projection
  - Weather-based generation alerts
- **Smart Alerts**: View, acknowledge, and configure time-based notifications
- **Usage Optimization**: AI-powered recommendations for optimal energy usage
- **Historical Analytics**: Energy production/consumption trends with weather correlation
- **Offline Mode**: Cached data and critical alerts when network unavailable

**Example Screen Layout:**
```
┌─────────────────────────────────┐
│ ☀️ Solar: 4.2kW  🔋 Battery: 85%  ☁️ 24°C │
│ 🏠 Load: 2.1kW   ⚡ Grid: +2.1kW  ☀️ 6.2h │
├─────────────────────────────────┤
│        Power Flow Diagram       │
│    [Solar] → [Battery] → [Load] │
│              ↓         ↗        │
│            [Grid] ←────         │
├─────────────────────────────────┤
│ Today: 28kWh ↗️ +12% vs avg     │
│ This hour: 2.1kWh (⏰ avg: 1.8kWh) │
│ Battery runtime: 6.2h @ current usage│
│ 🛁 Geyser time: 45min available   │
│ Sunshine today: 6.2h (proj: 7.1h)  │
│ Savings: R890 💰                │
└─────────────────────────────────┘
```

## Deployment Strategy

### Raspberry Pi Setup

**Hardware Requirements:**
- Raspberry Pi 4 (4GB+ RAM recommended)
- 32GB+ SD card (Class 10)
- Reliable internet connection
- Optional: UPS for power backup

**Docker Compose Deployment:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  influxdb:
    image: influxdb:2.0
    volumes:
      - influxdb_data:/var/lib/influxdb2
    environment:
      - INFLUXDB_DB=sunsynk
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=secretpassword
    ports:
      - "8086:8086"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  sunsynk-collector:
    build: ./collector
    depends_on:
      - influxdb
    environment:
      - SUNSYNK_USERNAME=${SUNSYNK_USERNAME}
      - SUNSYNK_PASSWORD=${SUNSYNK_PASSWORD}
      - WEATHER_API_KEY=${WEATHER_API_KEY}
      - LOCATION=${LOCATION}
      - INFLUXDB_URL=http://influxdb:8086
    restart: always

  sunsynk-analytics:
    build: ./analytics
    depends_on:
      - influxdb
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - ANALYSIS_INTERVAL=300  # 5 minutes
    restart: always

  sunsynk-api:
    build: ./dashboard
    ports:
      - "8000:8000"
    depends_on:
      - influxdb
      - sunsynk-analytics
    restart: always

  notification-engine:
    build: ./notifications
    depends_on:
      - influxdb
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
      - PHONE_NUMBER=${PHONE_NUMBER}
    restart: always

volumes:
  influxdb_data:
  grafana_data:
```

### Configuration Management

**Environment Variables (`.env`):**
```bash
# Sunsynk API
SUNSYNK_USERNAME=your_username
SUNSYNK_PASSWORD=your_password

# Weather API
WEATHER_API_KEY=your_openweather_api_key
LOCATION="City,Country"  # e.g., "Cape Town,ZA"

# Database
INFLUXDB_TOKEN=your_influx_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=sunsynk

# Notifications
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
WHATSAPP_FROM=+1234567890
SMS_TO=+1234567890
PHONE_NUMBER=+1234567890  # For voice calls

# Push Notifications
FCM_API_KEY=your_fcm_key

# Analytics Configuration
CONSUMPTION_THRESHOLD=2.5  # kW warning threshold
BATTERY_MIN_SOC=15  # Minimum battery level %
GEYSER_POWER_RATING=3.0  # kW rating of geyser
ANALYSIS_RETENTION_DAYS=365  # Days to keep detailed analysis
```

## Implementation Phases

### Phase 1: Core Data Collection (Week 1-2)
- Extend current Sunsynk client with persistent data storage
- Implement InfluxDB integration
- Create basic data collection service with error handling
- Add logging and monitoring

### Phase 2: Web Dashboard (Week 3-4)
- FastAPI backend with WebSocket support
- React.js frontend with real-time charts
- Historical data visualization
- Basic alert configuration interface

### Phase 3: Mobile Application (Week 5-8)
- React Native or Flutter app development
- Push notification setup
- Offline capability
- App store deployment

### Phase 4: Advanced Notifications (Week 9-10)
- WhatsApp/SMS integration via Twilio
- Rule-based alert engine
- Advanced alert customization interface

### Phase 5: Analytics & AI (Week 11-12)
- Predictive analytics for energy production
- Anomaly detection for equipment issues
- Cost optimization recommendations
- Weather correlation analysis

## Technology Stack Summary

**Backend:**
- Python 3.11+ (existing Sunsynk client)
- FastAPI (web API + WebSockets)
- InfluxDB (time-series database)
- Redis (caching, session management)

**Frontend:**
- React.js (web dashboard)
- Chart.js / D3.js (visualizations)
- WebSocket client (real-time updates)

**Mobile:**
- React Native or Flutter
- Firebase Cloud Messaging (push notifications)

**Notifications:**
- Twilio (WhatsApp, SMS, Voice)
- Firebase Cloud Messaging (mobile push)

**DevOps:**
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- Grafana (system monitoring)

This architecture provides a scalable, maintainable solution that transforms your Sunsynk API client into a comprehensive solar monitoring platform with enterprise-grade features while running efficiently on a Raspberry Pi.