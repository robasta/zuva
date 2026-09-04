"""Sunsynk Notification Service API.

Main module only defines FastAPI wiring and endpoint handlers.
"""
import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import Alert, NotificationSettings, TelemetryReading, USER_ID_PATTERN
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

# Set to a long random string. The service refuses to start without it: these
# endpoints can reconfigure where alerts are delivered and can send messages.
ZUVA_API_KEY = os.getenv("ZUVA_API_KEY")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

notification_service = NotificationService()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not ZUVA_API_KEY:
        raise RuntimeError(
            "ZUVA_API_KEY is not set. Set it to a long random string on both this "
            "service and the collector; refusing to start an unauthenticated "
            "notification API."
        )
    await notification_service.initialize()
    yield


app = FastAPI(title="Sunsynk Notification Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


async def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """Constant-time API key check for every endpoint except /health."""
    if not ZUVA_API_KEY or not secrets.compare_digest(x_api_key, ZUVA_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


UserId = Path(pattern=USER_ID_PATTERN)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "telegram_enabled": notification_service.telegram_bot is not None,
        "users_configured": len(notification_service.user_settings),
    }


@app.post("/settings", dependencies=[Depends(require_api_key)])
async def update_settings(settings: NotificationSettings):
    await notification_service.save_user_settings(settings)
    return {"status": "success", "user_id": settings.user_id}


@app.get("/settings/{user_id}", dependencies=[Depends(require_api_key)])
async def get_settings(user_id: str = UserId):
    settings = notification_service.user_settings.get(user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="User settings not found")
    return {
        "user_id": settings.user_id,
        "enabled_channels": settings.enabled_channels,
        "telegram_chat_id": settings.telegram_chat_id,
        "quiet_hours_start": settings.quiet_hours_start,
        "quiet_hours_end": settings.quiet_hours_end,
        "min_severity": settings.min_severity,
        "rate_limit_minutes": settings.rate_limit_minutes,
    }


@app.post("/alert", dependencies=[Depends(require_api_key)])
async def send_alert(alert: Alert, user_id: str = Query(default="default", pattern=USER_ID_PATTERN)):
    result = await notification_service.send_alert(alert, user_id)
    status = (result or {}).get("status", "sent")
    if status == "unknown_user":
        # Loud failure: an alert with nowhere to go is a configuration error,
        # not a successful delivery.
        raise HTTPException(status_code=409, detail=result.get("reason", "no settings for user"))
    if status == "failed":
        raise HTTPException(status_code=502, detail=result.get("reason", "delivery failed"))
    return result


@app.post("/telemetry", dependencies=[Depends(require_api_key)])
async def record_telemetry(reading: TelemetryReading):
    """Store one poll's readings. Called by the collector, which owns no database."""
    try:
        notification_service.history_store.record_reading(
            **reading.model_dump(exclude_none=True)
        )
    except Exception as exc:
        logger.exception("Could not store telemetry for inverter %s", reading.inverter_sn)
        raise HTTPException(status_code=500, detail="Could not store telemetry") from exc
    return {"status": "stored"}


@app.get("/alerts/history/{user_id}", dependencies=[Depends(require_api_key)])
async def get_alert_history(
    user_id: str = UserId,
    hours: int = Query(default=24, ge=1, le=8760),
):
    try:
        return notification_service.history_store.recent_alerts(user_id, hours)
    except Exception as exc:
        logger.exception("Alert history query failed for user %s", user_id)
        raise HTTPException(status_code=500, detail="Could not read alert history") from exc
