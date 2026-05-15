
"""
Sunsynk Notification Service API
Refactored: All logic in notification_service, models, db modules
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import asdict
import uvicorn
from .models import NotificationSettings, Alert, NotificationChannel, AlertSeverity, AlertCategory
from .notification_service import NotificationService

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notification_service = NotificationService()

@app.on_event("startup")
async def startup():
    await notification_service.initialize()

@app.on_event("shutdown")
async def shutdown():
    await notification_service.shutdown()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "telegram_enabled": notification_service.telegram_bot is not None,
        "users_configured": len(notification_service.user_settings)
    }

@app.post("/settings")
async def update_settings(settings: NotificationSettings):
    await notification_service.save_user_settings(settings)
    return {"status": "success", "user_id": settings.user_id}

@app.get("/settings/{user_id}")
async def get_settings(user_id: str):
    settings = notification_service.user_settings.get(user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    return asdict(settings)

@app.post("/alert")
async def send_alert(alert: Alert, user_id: str = "default"):
    await notification_service.send_alert(alert, user_id)
    return {"status": "sent"}

@app.get("/alerts/history/{user_id}")
async def get_alert_history(user_id: str, hours: int = 24):
    query = f'''
        from(bucket: "{notification_service.influx_client.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "alerts")
            |> filter(fn: (r) => r.user_id == "{user_id}")
    '''
    try:
        result = notification_service.query_api.query(query=query)
        alerts = []
        for table in result:
            for record in table.records:
                alerts.append({
                    "time": record.get_time(),
                    "category": record.values.get("category"),
                    "severity": record.values.get("severity"),
                    "title": record.values.get("title"),
                    "message": record.values.get("message")
                })
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
        # Save to InfluxDB
        point = Point("user_settings") \
            .tag("user_id", settings.user_id) \
            .field("enabled_channels", ",".join(user_settings.enabled_channels)) \
            .field("telegram_chat_id", user_settings.telegram_chat_id or "") \
            .field("quiet_hours_start", user_settings.quiet_hours_start) \
            .field("quiet_hours_end", user_settings.quiet_hours_end) \
            .field("min_severity", user_settings.min_severity) \
            .field("rate_limit_minutes", user_settings.rate_limit_minutes)
        
        self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        logger.info(f"Saved settings for user {settings.user_id}")
    
    def _is_quiet_hours(self, settings: UserSettings) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        start = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:  # Crosses midnight
            return now >= start or now <= end
    
    def _should_rate_limit(self, settings: UserSettings, category: str) -> bool:
        """Check if alert should be rate limited"""
        if category not in settings.last_alert_times:
            return False
        
        last_alert = settings.last_alert_times[category]
        minutes_since = (datetime.now() - last_alert).total_seconds() / 60
        
        return minutes_since < settings.rate_limit_minutes
    
    def _severity_check(self, alert_severity: AlertSeverity, min_severity: str) -> bool:
        """Check if alert severity meets minimum threshold"""
        severity_order = ["low", "medium", "high", "critical"]
        alert_idx = severity_order.index(alert_severity.value)
        min_idx = severity_order.index(min_severity)
        return alert_idx >= min_idx
    
    async def send_alert(self, alert: Alert, user_id: str = DEFAULT_USER_ID):
        """Send alert to user via configured channels"""
        if alert.category == AlertCategory.BATTERY_CRITICAL and alert.severity != AlertSeverity.CRITICAL:
            alert = alert.model_copy(update={"severity": AlertSeverity.CRITICAL})

        settings = self.user_settings.get(user_id)
        if not settings:
            logger.warning(f"No settings found for user {user_id}")
            return
        
        # Check severity threshold
        if not self._severity_check(alert.severity, settings.min_severity):
            logger.info(f"Alert {alert.category} below minimum severity threshold")
            return
        
        # Check quiet hours (except for critical alerts)
        if alert.severity != AlertSeverity.CRITICAL and self._is_quiet_hours(settings):
            logger.info(f"Skipping alert {alert.category} during quiet hours")
            return
        
        # Check rate limiting
        if self._should_rate_limit(settings, alert.category.value):
            logger.info(f"Rate limiting alert {alert.category}")
            return
        
        # Send to enabled channels
        success = False
        for channel in settings.enabled_channels:
            if channel == NotificationChannel.TELEGRAM.value:
                if await self._send_telegram(alert, settings):
                    success = True
        
        # Update last alert time
        if success:
            settings.last_alert_times[alert.category.value] = datetime.now()
            
            # Log alert to InfluxDB
            point = Point("alerts") \
                .tag("user_id", user_id) \
                .tag("category", alert.category.value) \
                .tag("severity", alert.severity.value) \
                .field("title", alert.title) \
                .field("message", alert.message)
            
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    
    async def _send_telegram(self, alert: Alert, settings: UserSettings) -> bool:
        """Send alert via Telegram"""
        if not self.telegram_bot or not settings.telegram_chat_id:
            logger.warning("Telegram not configured for this user")
            return False
        
        try:
            # Format message with emoji based on severity
            emoji = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🔥",
                AlertSeverity.CRITICAL: "🚨"
            }[alert.severity]
            
            message = f"{emoji} **{alert.title}**\n\n{alert.message}"
            
            if alert.metadata:
                message += "\n\n📊 Details:\n"
                for key, value in alert.metadata.items():
                    message += f"• {key}: {value}\n"
            
            response = await self.telegram_bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message
            )
            logger.info(
                "Sent Telegram alert to %s (message_id=%s)",
                settings.telegram_chat_id,
                getattr(response, "message_id", None),
            )
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.influx_client:
            self.influx_client.close()


# FastAPI app
app = FastAPI(title="Sunsynk Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


notification_service = NotificationService()



@app.on_event("startup")
async def startup():
    await notification_service.initialize()



@app.on_event("shutdown")
async def shutdown():
    await notification_service.shutdown()



@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "telegram_enabled": notification_service.telegram_bot is not None,
        "users_configured": len(notification_service.user_settings)
    }



@app.post("/settings")
async def update_settings(settings: NotificationSettings):
    await notification_service.save_user_settings(settings)
    return {"status": "success", "user_id": settings.user_id}



@app.get("/settings/{user_id}")
async def get_settings(user_id: str):
    settings = notification_service.user_settings.get(user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    return asdict(settings)



@app.post("/alert")
async def send_alert(alert: Alert, user_id: str = "default"):
    await notification_service.send_alert(alert, user_id)
    return {"status": "sent"}



@app.get("/alerts/history/{user_id}")
async def get_alert_history(user_id: str, hours: int = 24):
    query = f'''
        from(bucket: "{notification_service.influx_client.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "alerts")
            |> filter(fn: (r) => r.user_id == "{user_id}")
    '''
    try:
        result = notification_service.query_api.query(query=query)
        alerts = []
        for table in result:
            for record in table.records:
                alerts.append({
                    "time": record.get_time(),
                    "category": record.values.get("category"),
                    "severity": record.values.get("severity"),
                    "title": record.values.get("title"),
                    "message": record.values.get("message")
                })
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    api_port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=api_port)
