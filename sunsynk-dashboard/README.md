# Sunsynk Solar Dashboard & Notification System

A comprehensive solar monitoring system that transforms the Sunsynk API client into a real-time dashboard with intelligent notifications, consumption analytics, and mobile integration. Designed to run on Raspberry Pi with 24/7 monitoring capabilities.

## Features

### 🌟 Core Capabilities
- **Real-time Monitoring**: Live power flow visualization and metrics
- **Historical Analytics**: Hourly, daily, and monthly consumption patterns
- **Weather Integration**: Sunshine hours, forecasts, and solar production correlation
- **Battery Intelligence**: Runtime calculations and geyser usage optimization
- **Multi-channel Notifications**: WhatsApp, SMS, Push notifications, and Voice calls
- **Mobile Application**: Cross-platform app with offline capabilities
- **Time-based Alerts**: Conditional alerts based on time of day and battery status

### 📊 Dashboard Features
- **Power Flow Diagram**: Real-time visualization of solar, battery, grid, and load
- **Consumption Analytics**: Detailed energy usage patterns and trends
- **Weather Dashboard**: Current conditions and production forecasts
- **Battery Intelligence**: Runtime projections and optimization recommendations
- **Financial Tracking**: Cost savings and efficiency metrics
- **Alert Management**: Configure and monitor system notifications

### 🔔 Intelligent Notifications
- **Battery Alerts**: Full charge, low SOC during peak hours, critical warnings
- **Weather Alerts**: Low sunshine projections and continuous cloud cover
- **Consumption Alerts**: High usage warnings and threshold breaches
- **System Alerts**: Grid outages and inverter connectivity issues
- **Voice Calls**: Critical battery situations with high consumption

## Environment Variables

Create a `.env` file in the dashboard root directory with the following variables:

### Required for Real Data Collection
```bash
# Sunsynk API Credentials
SUNSYNK_USERNAME=your_sunsynk_username
SUNSYNK_PASSWORD=your_sunsynk_password

# Weather API
OPENWEATHER_API_KEY=your_openweather_api_key
LOCATION=Randburg,ZA

# Database
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=sunsynk
INFLUXDB_BUCKET=solar_metrics

# Security
JWT_SECRET_KEY=your_jwt_secret_key

# Data Source Control
USE_MOCK_DATA=false
DISABLE_MOCK_FALLBACK=false
```

### Data Source Configuration
- `USE_MOCK_DATA=true`: Forces the application to use only mock data
- `DISABLE_MOCK_FALLBACK=true`: Prevents fallback to mock data when real data fails (returns errors instead)
- `DISABLE_MOCK_FALLBACK=false`: Allows fallback to mock data when real data is unavailable (default)

### Important Security Notes
- Never commit the `.env` file to version control
- Keep your Sunsynk credentials secure
- Regenerate tokens periodically
- Use strong JWT secret keys in production

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Sunsynk Connect account credentials
- OpenWeatherMap API key (free)
- Optional: Twilio account for notifications

### 1. Clone and Setup
```bash
git clone <repository-url>
cd sunsynk-dashboard
cp .env.template .env
# Edit .env with your credentials
```

### 2. Configure Environment
Edit `.env` file with your settings:
```bash
# Required
SUNSYNK_USERNAME=your_username
SUNSYNK_PASSWORD=your_password
WEATHER_API_KEY=your_openweather_key

# Optional (for notifications)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

### 3. Deploy
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access Dashboards
- **Web Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Grafana Monitoring**: http://localhost:3001 (admin/admin)
- **InfluxDB**: http://localhost:8086

## Architecture

### System Components
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Sunsynk API │◄──►│ Data Collector│◄──►│ InfluxDB    │
└─────────────┘    └──────────────┘    └─────────────┘
                           │                     │
┌─────────────┐            ▼                     ▼
│ Weather API │◄─── ┌──────────────┐    ┌─────────────┐
└─────────────┘     │ Analytics    │◄──►│ Dashboard   │
                    │ Engine       │    │ API         │
                    └──────────────┘    └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐    ┌─────────────┐
                    │ Notification │    │ Web/Mobile  │
                    │ Engine       │    │ Frontend    │
                    └──────────────┘    └─────────────┘
```

### Service Breakdown
- **Data Collector**: Polls Sunsynk API every 30 seconds, stores in InfluxDB
- **Weather Collector**: Fetches weather data and sunshine forecasts
- **Analytics Engine**: Processes consumption patterns and predictions
- **Dashboard API**: FastAPI backend with WebSocket real-time updates
- **Web Frontend**: React.js responsive dashboard
- **Notification Engine**: Multi-channel alert system
- **Nginx**: Reverse proxy and SSL termination
- **Grafana**: System monitoring and advanced visualizations

## Configuration

### Alert Rules
Configure alerts in `config/alerts.yaml`:
```yaml
alerts:
  battery_low_daytime:
    condition: "battery_soc < 65 AND hour >= 11 AND hour <= 18"
    severity: "warning"
    channels: ["whatsapp", "push"]
    cooldown: "1h"
    
  battery_critical_high_usage:
    condition: "battery_soc <= 15 AND load_power > 0.4"
    severity: "critical"
    channels: ["voice_call", "sms", "whatsapp"]
    cooldown: "5min"
```

### Data Collection
- **Polling Interval**: 30 seconds (configurable)
- **Data Retention**: 1 year detailed, 5 years aggregated
- **Weather Updates**: Every 15 minutes
- **Analytics Processing**: Every 5 minutes

## Mobile App

### Installation
- **Android**: Download APK or install via Google Play Store
- **iOS**: Install via Apple App Store (requires Apple Developer account)
- **Progressive Web App**: Access via mobile browser

### Features
- Real-time power flow visualization
- Consumption analytics with graphs
- Battery runtime calculator
- Weather integration and forecasts
- Push notifications and alert management
- Offline mode with data synchronization

## Notifications

### Supported Channels
1. **WhatsApp**: Via Twilio WhatsApp API
2. **SMS**: Standard text messages via Twilio
3. **Push Notifications**: Mobile app via Firebase
4. **Voice Calls**: Automated voice alerts for critical situations
5. **Email**: SMTP-based email notifications

### Alert Types
- **Battery Status**: Full, low SOC, critical levels
- **Weather**: Low sunshine, continuous cloud cover
- **Consumption**: High usage, threshold breaches
- **System**: Grid outages, inverter offline
- **Time-based**: Conditional alerts based on time of day

## Monitoring & Maintenance

### Health Checks
```bash
# Check all services
docker-compose ps

# View service logs
docker-compose logs -f data-collector
docker-compose logs -f notification-engine

# Database status
curl http://localhost:8086/health
```

### Backup & Recovery
```bash
# Backup InfluxDB data
docker-compose exec influxdb influx backup /backup

# Backup configuration
tar -czf config-backup.tar.gz config/ .env
```

### Performance Optimization
- **Raspberry Pi 4**: Recommended 4GB+ RAM
- **Storage**: Use SSD instead of SD card for better performance
- **Network**: Stable internet connection required
- **Power**: UPS recommended for continuous operation

## Development

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run data collector locally
cd collector
python data_collector.py

# Run dashboard API
cd dashboard
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Run React frontend
cd dashboard/frontend
npm start
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Test notifications
python -m pytest tests/test_notifications.py

# Integration tests
python -m pytest tests/integration/
```

### API Documentation
- **OpenAPI Spec**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **WebSocket**: ws://localhost:8000/ws

## Deployment

### Raspberry Pi Setup
1. **Install Docker**: `curl -fsSL https://get.docker.com | sh`
2. **Clone Repository**: `git clone <repo-url>`
3. **Configure Environment**: Copy and edit `.env` file
4. **Deploy**: `docker-compose up -d`
5. **Setup Auto-start**: Enable Docker service autostart

### Cloud Deployment
- **AWS/Azure/GCP**: Use container services (ECS, ACI, Cloud Run)
- **VPS**: Any Linux server with Docker support
- **DigitalOcean**: App Platform or Droplets

### SSL/HTTPS Setup
1. **Domain**: Point your domain to the server IP
2. **Certificates**: Use Let's Encrypt via Certbot
3. **Nginx**: Configure SSL termination
4. **Firewall**: Open ports 80 and 443

## Troubleshooting

### Common Issues
1. **API Connection**: Check Sunsynk credentials and internet connectivity
2. **Database**: Ensure InfluxDB is running and accessible
3. **Notifications**: Verify Twilio credentials and phone numbers
4. **Performance**: Monitor resource usage on Raspberry Pi

### Support
- **Documentation**: Check architecture docs and API references
- **Logs**: Review service logs for error details
- **Health Checks**: Use built-in endpoints to verify system status
- **Community**: GitHub issues and discussions

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## Roadmap

### ✅ Phase 1: COMPLETED (Core Dashboard)
- Real-time solar monitoring with InfluxDB time-series storage
- Basic analytics and consumption tracking
- Production-ready deployment architecture

### ✅ Phase 2: COMPLETED (Advanced Analytics)
- **Machine Learning Battery Predictor**: Multi-horizon SOC forecasting (1h, 4h, 24h)
- **Weather Correlation Analyzer**: Intelligent weather-solar correlation analysis
- **Usage Optimization Engine**: AI-driven device scheduling and load optimization
- **Enhanced Demo**: Real-time advanced analytics with ML predictions
- **Risk Assessment**: Multi-dimensional energy risk analysis

### 🚧 Phase 3: Ready for Implementation (Web Dashboard)
- Web dashboard with real-time API endpoints
- Interactive charts and advanced visualization
- Mobile app support with offline capabilities
- Enhanced notification and alert systems
- User authentication and multi-tenant support

### 🔮 Future Phases
- [ ] Machine learning for consumption prediction
- [ ] Advanced anomaly detection
- [ ] Integration with home automation systems
- [ ] Multi-site monitoring support
- [ ] Advanced financial analytics
- [ ] Carbon footprint tracking

## Demo Commands

### Phase 1 Demo (Basic Monitoring)
```bash
cd sunsynk-dashboard
python3 demo_runner.py
```

### Phase 2 Demo (Advanced Analytics)
```bash
cd sunsynk-dashboard
# Phase 2 includes ML predictions, weather correlation, optimization
python3 demo_runner.py
```

**Phase 2 Demo Features:**
- 🤖 Machine learning battery predictions with confidence scoring
- 🌤️ Weather correlation analysis and solar forecasting
- 🎯 Intelligent optimization recommendations with savings calculations
- 🏠 Smart device scheduling (geyser, pool pump, HVAC)
- ⚠️ Risk assessment and mitigation strategies
- 📊 Real-time analytics processing with sub-second performance