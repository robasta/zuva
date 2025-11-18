# Sunsynk Dashboard Mobile – Backend Contract

_Last updated: 2025-11-18_

This document captures the REST and WebSocket contracts required by the planned mobile clients. The information is sourced from the Phase 6 backend implementation in `sunsynk-dashboard/backend/main.py` and serves as the source of truth for API integration during mobile development.

## 1. Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | None | Exchange username/password for a JWT bearer token.

**Request body**

```jsonc
{
  "username": "demo",
  "password": "demo123"
}
```

**Response body** (`LoginResponse`)

```jsonc
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 86400
}
```

The returned JWT must be supplied via `Authorization: Bearer <token>` on all subsequent calls. Tokens expire after 24 hours (configurable by `JWT_EXPIRATION_HOURS`).

## 2. Dashboard Data

| Endpoint | Method | Query | Description |
|----------|--------|-------|-------------|
| `/api/dashboard/current` | GET | — | Current inverter metrics plus status flags and weather snapshot.|
| `/api/dashboard/history` | GET | `hours` (int, default 24) | Aggregated historical metrics.|
| `/api/dashboard/timeseries` | GET | `start_time` (string, default `-24h`), `resolution` (string, default `15m`) | Time series points for dashboard charts.

### `/api/dashboard/current`

**Response**

```jsonc
{
  "metrics": {
    "timestamp": "2025-11-18T06:15:42.025718",
    "solar_power": 2.8,
    "battery_level": 76.2,
    "grid_power": -0.5,
    "consumption": 2.3,
    "weather_condition": "clear",
    "temperature": 22.1
  },
  "status": {
    "online": true,
    "last_update": "2025-11-18T06:15:42.025718",
    "inverter_status": "online",
    "battery_status": "normal",
    "grid_status": "connected"
  },
  "weather_forecast": [
    {
      "timestamp": "2025-11-18T09:00:00",
      "condition": "sunny",
      "temperature": 25.0
    }
  ]
}
```

### `/api/dashboard/history`

**Response**

```jsonc
{
  "history": [
    {
      "timestamp": "2025-11-18T06:00:00",
      "solar_power": 2.4,
      "battery_level": 75.0,
      "grid_power": -0.4,
      "consumption": 2.0,
      "battery_power": 0.5
    }
  ],
  "source": "influxdb",
  "count": 48
}
```

### `/api/dashboard/timeseries`

**Response** (post deduplication fix, returning unique timestamps)

```jsonc
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-11-18T06:00:00.000000Z",
      "generation": 1.92,
      "consumption": 2.35,
      "battery_soc": 73.4,
      "battery_level": 73.4
    }
  ],
  "source": "influxdb",
  "count": 96,
  "resolution": "15m",
  "time_span": "24h"
}
```

## 3. Alerts & Notifications

| Endpoint | Method | Query | Description |
|----------|--------|-------|-------------|
| `/api/alerts` | GET | `status`, `severity`, `hours` | Fetch active and historical alerts. |
| `/api/alerts/{alert_id}/acknowledge` | POST | — | Acknowledge an alert. |
| `/api/alerts/{alert_id}/resolve` | POST | — | Resolve an alert. |
| `/api/alerts/test` | POST | `severity` | Create a test alert (useful for mobile QA). |

**GET `/api/alerts` response**

```jsonc
{
  "alerts": [
    {
      "id": "f3f0dd06-6c1c-42d9-9128-8e2f1764bc76",
      "title": "Battery Level Low",
      "message": "Battery at 25.0% - Consider reducing consumption",
      "severity": "medium",
      "status": "active",
      "category": "battery_low",
      "timestamp": "2025-11-18T05:45:00",
      "acknowledged_at": null,
      "resolved_at": null,
      "metadata": {
        "current_soc": 25.0
      }
    }
  ]
}
```

### WebSocket Notifications

| Endpoint | Description |
|----------|-------------|
| `/ws/dashboard` | Bi-directional WebSocket streaming real-time system updates and alert notifications. |

Messages are JSON strings with the structure emitted in `_send_push_notification`:

```jsonc
{
  "type": "alert_notification",
  "data": {
    "id": "...",
    "title": "...",
    "message": "...",
    "severity": "low|medium|high|critical",
    "category": "battery_low",
    "timestamp": "2025-11-18T06:12:30.000Z"
  }
}
```

Mobile clients must reconnect on disconnect and surface notifications via the local notification framework.

## 4. Settings & Preferences

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Fetch all settings for the authenticated user grouped by category. |
| `/api/settings/{category}` | GET | Fetch settings for a single category. |
| `/api/settings/{category}` | PUT | Bulk update settings within a category. |
| `/api/settings/{category}/{key}` | GET/PUT/DELETE | CRUD for individual settings. |
| `/api/settings/weather/location` | GET/PUT | Manage weather location preferences. |
| `/api/notifications/preferences` | GET/PUT | Access notification channel configuration. |

Settings are user-scoped and require the authenticated user’s `sub` claim. Requests return structures compatible with the `NotificationPreferences` and various configuration models declared in `main.py`.

## 5. Analytics & ML Endpoints

| Endpoint | Method | Query | Description |
|----------|--------|-------|-------------|
| `/api/v6/weather/correlation` | GET | `days` (default 7) | Weather correlation analysis for solar performance. |
| `/api/v6/consumption/patterns` | GET | `days` (default 30) | Consumption pattern insight. |
| `/api/v6/battery/optimization` | GET | — | Recommended battery charge/discharge schedule. |
| `/api/v6/analytics/forecasting` | GET | `hours` (default 48) | Forecasted production/consumption data. |

Responses include nested summary objects and arrays as defined in the backend; mobile clients should deserialize them verbatim using Kotlin Serialization data models.

## 6. System Monitoring & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Basic service health metadata, including InfluxDB status and feature flags. |
| `/api/system/monitor` | GET | Real-time monitoring data and currently active alert counts. |

## 7. Error Handling

Errors follow standard FastAPI responses, typically:

```jsonc
{
  "detail": "Error message"
}
```

Mobile clients should map `HTTP 503` from `/api/dashboard/timeseries` when mock fallback is disabled, and `HTTP 401` responses trigger token refresh or force logout.

## 8. Data Serialization Notes

- All timestamps from InfluxDB are emitted as ISO-8601 strings; existing logic now guarantees unique timestamps per interval.
- Alert severity enumerations align with `AlertSeverity` (low, medium, high, critical).
- Battery fields may be present as both `battery_soc` and `battery_level`; treat them as aliases.
- Weather structures contain optional fields (`weather_condition`, `cloud_cover`); use nullable types in the shared data models.

## 9. Open Questions

1. Should mobile clients support pagination for alerts, or is time-based filtering sufficient? (Current API supports `hours` filtering only.)
2. Are we standardising on metric units (kW, %) across all responses? The backend currently emits floats without unit metadata.
3. Do we need a dedicated endpoint for real-time streaming beyond the existing WebSocket channel?

Please raise backend contract changes via PR to keep this document authoritative.
