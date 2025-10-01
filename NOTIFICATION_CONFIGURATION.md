# 🔔 Sunsynk Dashboard Notification System Configuration

## Overview

The Sunsynk Dashboard notification system provides comprehensive multi-channel alert capabilities with real-time monitoring of your solar power system. This guide covers all configuration options for setting up notifications including email, SMS, WhatsApp, voice calls, and push notifications.

## 📋 Supported Notification Channels

| Channel | Status | Configuration Required | Use Case |
|---------|--------|----------------------|----------|
| **Push Notifications** | ✅ Active | None (Built-in) | Real-time browser alerts |
| **Email** | 🔧 Setup Required | SMTP Configuration | Detailed alert summaries |
| **SMS** | 🔧 Setup Required | Twilio Account | Instant text alerts |
| **WhatsApp** | 🔧 Setup Required | Twilio Business API | Rich media notifications |
| **Voice Calls** | 🔧 Setup Required | Twilio Voice API | Critical emergency alerts |

---

## 🚀 Quick Start Configuration

### Step 1: Environment Setup

Copy and configure your environment file:

```bash
cd sunsynk-dashboard
cp .env.template .env
nano .env  # Edit with your settings
```

### Step 2: Minimal Working Configuration

For basic functionality with push notifications only:

```bash
# Essential settings - replace with your actual values
SUNSYNK_USERNAME=your_sunsynk_username
SUNSYNK_PASSWORD=your_sunsynk_password
WEATHER_API_KEY=your_openweather_api_key
JWT_SECRET_KEY=your-256-bit-secret-key

# Database (uses existing InfluxDB)
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=sunsynk
INFLUXDB_BUCKET=solar_metrics
```

### Step 3: Test Your Setup

Start the system and verify push notifications work:

```bash
# Start backend
python3 sunsynk-dashboard/backend/main.py

# Start frontend  
cd sunsynk-dashboard/frontend && npm start

# Test notifications (in another terminal)
curl -X POST "http://localhost:8001/api/alerts/test?severity=critical"
```

---

## 📧 Email Notifications Configuration

### Gmail Setup (Recommended)

```bash
# Gmail SMTP Configuration
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your.email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
EMAIL_FROM=your.email@gmail.com
EMAIL_TO=recipient@gmail.com
```

**Gmail App Password Setup:**
1. Enable 2-Factor Authentication on your Gmail account
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Navigate to **App passwords** section
4. Generate a new app password for "Mail"
5. Use this 16-character password (not your regular Gmail password)

### Outlook/Hotmail Setup

```bash
EMAIL_SMTP_HOST=smtp-mail.outlook.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your.email@outlook.com
EMAIL_PASSWORD=your_outlook_password
EMAIL_FROM=your.email@outlook.com
EMAIL_TO=recipient@outlook.com
```

### Corporate/Custom SMTP

```bash
EMAIL_SMTP_HOST=mail.yourcompany.com
EMAIL_SMTP_PORT=587  # or 465 for SSL
EMAIL_USERNAME=notifications@yourcompany.com
EMAIL_PASSWORD=your_smtp_password
EMAIL_FROM=solar-alerts@yourcompany.com
EMAIL_TO=admin@yourcompany.com
```

### Email Template Customization

Email alerts include:
- **Subject**: `[Sunsynk Alert] {severity} - {title}`
- **Body**: Detailed alert information with timestamp
- **HTML Format**: Rich formatting with severity color coding
- **Attachments**: Optional system status reports

---

## 📱 SMS & WhatsApp Configuration (Twilio)

### Step 1: Twilio Account Setup

1. **Create Account**: Sign up at [twilio.com](https://www.twilio.com)
2. **Verify Phone**: Complete phone number verification
3. **Get Credentials**: Note your Account SID and Auth Token
4. **Purchase Number**: Buy a Twilio phone number

### Step 2: Basic Twilio Configuration

```bash
# Twilio Credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_32_character_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Recipient Configuration
SMS_TO=+1234567890        # Your mobile number
VOICE_TO=+1234567890      # Number for emergency calls
```

### Step 3: WhatsApp Business API Setup

```bash
# WhatsApp Configuration (requires Twilio approval)
WHATSAPP_FROM=whatsapp:+1234567890  # Your Twilio WhatsApp number
WHATSAPP_TO=whatsapp:+1234567890    # Recipient WhatsApp number
```

**WhatsApp Requirements:**
- Business account verification through Twilio
- Pre-approved message templates
- 24-hour messaging window limitations
- Higher cost per message

### Step 4: Voice Call Configuration

Voice calls are automatically enabled when Twilio is configured. They trigger for:

- **Critical Battery Alerts** (< 10% battery level)
- **System Emergency Conditions**
- **Grid Failure with Low Battery**

Voice call features:
- Text-to-speech alert messages
- Configurable retry attempts
- Emergency contact escalation
- Respects quiet hours (except critical alerts)

---

## 🔔 Push Notifications Setup

### Real-time WebSocket Notifications

Push notifications work automatically through WebSocket connections. No external configuration needed.

**Features:**
- Instant browser notifications
- Toast messages for new alerts
- Real-time dashboard updates
- Notification center with history
- Desktop notification permissions

### Firebase Cloud Messaging (Optional)

For mobile app notifications (future enhancement):

```bash
# Firebase Configuration
FCM_API_KEY=your_firebase_api_key
FCM_SENDER_ID=your_sender_id
FCM_PROJECT_ID=your_project_id
```

---

## ⚙️ Alert Configuration & Thresholds

### System Monitoring Conditions

The system monitors these conditions automatically:

| Condition | Default Threshold | Severity | Action |
|-----------|------------------|----------|---------|
| **Battery Low** | < 20% | Medium | Email + SMS |
| **Battery Critical** | < 10% | Critical | All channels + Voice |
| **Grid Outage** | No grid power | High | Email + SMS + Push |
| **Inverter Offline** | No response | High | All channels |
| **High Consumption** | > 5kW | Medium | Push + Email |
| **Weather Poor** | < 20% efficiency | Low | Push only |
| **Battery Not Charging** | No charge in daylight | Medium | Email + Push |

### Customizing Alert Thresholds

Update alert sensitivity in your configuration:

```bash
# Alert Thresholds
BATTERY_LOW_THRESHOLD=20          # Percentage
BATTERY_CRITICAL_THRESHOLD=10     # Percentage  
HIGH_CONSUMPTION_THRESHOLD=5.0    # kW
WEATHER_EFFICIENCY_THRESHOLD=0.2  # 20%
GRID_OUTAGE_DURATION=300         # 5 minutes
```

### Notification Preferences

Configure when and how alerts are sent:

```bash
# Quiet Hours (24-hour format)
QUIET_HOURS_START=22:00  # 10 PM
QUIET_HOURS_END=06:00    # 6 AM

# Rate Limiting
MAX_NOTIFICATIONS_PER_HOUR=4     # Prevent spam
EMERGENCY_VOICE_CALLS=true       # Critical alerts only
NOTIFICATION_RETRY_ATTEMPTS=3    # Failed delivery retries
```

---

## 🔐 Security & Authentication

### JWT Configuration

```bash
# Security Settings
JWT_SECRET_KEY=your-super-secret-256-bit-key
JWT_EXPIRATION_HOURS=24
JWT_ALGORITHM=HS256
```

**Generate a secure JWT secret:**
```bash
# Generate a secure 256-bit key
openssl rand -hex 32
```

### User Management

```bash
# Default Users (Change in Production!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password_immediately
DEMO_USERNAME=demo  
DEMO_PASSWORD=demo123
```

### API Security

```bash
# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
API_RATE_LIMIT=100  # Requests per minute per IP
ENABLE_API_DOCS=true  # Set false in production
```

---

## 📊 Database & Storage Configuration

### InfluxDB Setup

```bash
# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=sunsynk
INFLUXDB_BUCKET=solar_metrics
INFLUXDB_RETENTION_DAYS=365
```

### Alert Storage

```bash
# Alert Retention
ALERT_RETENTION_DAYS=90      # Keep alerts for 90 days
ALERT_CLEANUP_INTERVAL=24    # Hours between cleanup
MAX_ALERTS_PER_CONDITION=100 # Prevent database bloat
```

---

## 🔧 Advanced Configuration

### Webhook Notifications

For integration with external systems:

```bash
# Webhook Configuration
WEBHOOK_URL=https://your-system.com/webhooks/sunsynk
WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_TIMEOUT=30  # seconds
WEBHOOK_RETRY_ATTEMPTS=3
```

### Custom Notification Templates

```bash
# Template Configuration
EMAIL_TEMPLATE_PATH=./templates/email/
SMS_TEMPLATE_PATH=./templates/sms/
VOICE_TEMPLATE_PATH=./templates/voice/
USE_CUSTOM_TEMPLATES=true
```

### Performance Tuning

```bash
# Performance Settings
WEBSOCKET_MAX_CONNECTIONS=100
NOTIFICATION_QUEUE_SIZE=1000
ASYNC_NOTIFICATION_WORKERS=5
DATABASE_CONNECTION_POOL=10
```

---

## 🧪 Testing Your Configuration

### Built-in Test Endpoints

Test individual notification channels:

```bash
# Test all channels
curl -X POST "http://localhost:8001/api/alerts/test?severity=critical" \
  -H "Authorization: Bearer $TOKEN"

# Test specific channels
curl -X POST "http://localhost:8001/api/notifications/test/email" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8001/api/notifications/test/sms" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8001/api/notifications/test/voice" \
  -H "Authorization: Bearer $TOKEN"
```

### Configuration Health Check

```bash
# Check notification system health
curl -X GET "http://localhost:8001/api/notifications/health" \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
{
  "status": "healthy",
  "channels": {
    "push": "active",
    "email": "configured",
    "sms": "configured", 
    "whatsapp": "requires_approval",
    "voice": "configured"
  }
}
```

### Test Alert Scenarios

```bash
# Simulate different alert conditions
curl -X POST "http://localhost:8001/api/alerts/simulate/battery_low" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8001/api/alerts/simulate/grid_outage" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8001/api/alerts/simulate/battery_critical" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔍 Troubleshooting

### Common Configuration Issues

#### 1. Email Not Working

**Problem**: Emails not being sent
**Solutions**:
```bash
# Check SMTP configuration
telnet smtp.gmail.com 587

# Verify Gmail app password
# Check firewall/antivirus blocking SMTP
# Test with different SMTP provider
```

#### 2. Twilio SMS/Voice Failures

**Problem**: SMS or voice calls not working
**Solutions**:
- Verify Account SID and Auth Token
- Check phone number format (+country code)
- Ensure sufficient Twilio account credits
- Verify phone number is not on suppression list

#### 3. Push Notifications Not Appearing

**Problem**: WebSocket notifications not working
**Solutions**:
- Check browser notification permissions
- Verify WebSocket connection in dev tools
- Check CORS configuration
- Ensure frontend/backend URLs match

#### 4. Database Connection Issues

**Problem**: InfluxDB connection failures
**Solutions**:
```bash
# Test InfluxDB connection
curl -X GET "http://localhost:8086/health"

# Check InfluxDB token permissions
# Verify bucket exists
# Check network connectivity
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Debug Configuration
LOG_LEVEL=DEBUG
ENABLE_NOTIFICATION_LOGGING=true
ENABLE_WEBSOCKET_LOGGING=true
ENABLE_DATABASE_LOGGING=true
```

### Error Monitoring

Monitor notification system health:

```bash
# Health monitoring endpoints
GET /api/notifications/status
GET /api/system/health  
GET /api/alerts/statistics
```

---

## 🚀 Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong JWT secret (256-bit)
- [ ] Enable HTTPS for all endpoints
- [ ] Restrict CORS to production domains
- [ ] Set up proper firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable API rate limiting
- [ ] Regular security updates

### Performance Optimization

- [ ] Configure database connection pooling
- [ ] Set up notification queue processing
- [ ] Enable gzip compression
- [ ] Configure CDN for frontend assets
- [ ] Set up monitoring and alerting
- [ ] Implement log rotation
- [ ] Configure backup strategies

### Monitoring & Maintenance

```bash
# Monitoring Configuration
ENABLE_METRICS=true
METRICS_RETENTION_DAYS=30
ALERT_ON_NOTIFICATION_FAILURES=true
HEALTH_CHECK_INTERVAL=60  # seconds
```

---

## 📞 Support & Documentation

### API Documentation

When the system is running, access interactive API docs at:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Configuration Examples

See the `/examples` directory for:
- Sample environment files
- Docker configurations  
- Kubernetes deployments
- Notification templates

### Need Help?

1. **Check logs**: Review backend logs for error details
2. **Test endpoints**: Use built-in testing endpoints
3. **Health checks**: Monitor system health endpoints
4. **Documentation**: Refer to API documentation
5. **Community**: Check project discussions and issues

---

## 📝 Configuration Summary

This notification system provides enterprise-grade alerting capabilities for your Sunsynk solar installation. The multi-channel approach ensures you never miss critical alerts while the intelligent filtering prevents notification spam.

**Key Features Implemented:**
- ✅ REQ-005: Multi-channel notification system  
- ✅ REQ-013: Time-based conditional alerts
- ✅ REQ-014: Voice call alerts for critical battery events
- ✅ Real-time WebSocket notifications
- ✅ Intelligent rate limiting and quiet hours
- ✅ Comprehensive alert management
- ✅ Production-ready security

Start with push notifications for immediate functionality, then gradually configure additional channels based on your needs. Each channel can be independently enabled/disabled and customized to your preferences.