"""
Sunsynk Notification Service API.
Main module only defines FastAPI wiring and endpoint handlers.
"""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import INFLUXDB_BUCKET
from .models import Alert, NotificationSettings
from .notification_service import NotificationService

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
        "users_configured": len(notification_service.user_settings),
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
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "alerts")
            |> filter(fn: (r) => r.user_id == "{user_id}")
    '''

    try:
        result = notification_service.query_api.query(query=query)
        alerts = []
        for table in result:
            for record in table.records:
                alerts.append(
                    {
                        "time": record.get_time(),
                        "category": record.values.get("category"),
                        "severity": record.values.get("severity"),
                        "title": record.values.get("title"),
                        "message": record.values.get("message"),
                    }
                )
        return alerts
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
