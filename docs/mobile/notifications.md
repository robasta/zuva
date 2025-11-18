# Mobile Notification Architecture

_Last updated: 2025-11-18_

This document records the notification pipeline for the Sunsynk dashboard mobile clients and links each step to the existing backend implementation.

## 1. Server-Side Pipeline Verification

| Capability | Status | Source |
|------------|--------|--------|
| Alert broadcast via WebSocket | ✅ Implemented in `ConnectionManager.broadcast` and `_send_push_notification` within `sunsynk-dashboard/backend/main.py`. |
| Alert persistence | ✅ Alerts stored through `AlertManager.save_alert_to_db`; relies on `collector.database.db_manager`. |
| Email/SMS/WhatsApp stubs | 🚧 Placeholders only (`_send_email`, `_send_sms`, `_send_whatsapp`, `_send_voice_call`). |
| Quiet hours & rate limiting | ✅ `_is_quiet_hours` and `_is_rate_limited` enforce notification throttling. |
| Test alert generator | ✅ `/api/alerts/test` endpoint triggers full pipeline for QA.

Mobile clients will rely on the WebSocket push channel for near real-time alerts. Additional push transport (FCM/Huawei Push Kit) can be layered later by reusing the existing alert creation hooks.

## 2. Mobile Notification Flow

1. **Session established**: Mobile app authenticates via `/api/auth/login`, then connects to `/ws/dashboard` using the bearer token.
2. **WebSocket listener**: Shared KMP module provides a `SunsynkAlertStream` that listens for `alert_notification` messages.
3. **Local dispatch**: Android app raises a `NotificationCompat` notification per alert severity and updates in-app state.
4. **Acknowledgement/Resolution**: User actions call `/api/alerts/{id}/acknowledge` or `/resolve`, which in turn update the backend and are broadcast through the same WebSocket for all clients.

## 3. Channel Mapping (Android)

| Severity | Channel ID | Importance | Style |
|----------|-------------|------------|--------|
| critical | `alerts_critical` | `IMPORTANCE_HIGH` | Full-screen intent optional |
| high | `alerts_high` | `IMPORTANCE_HIGH` | Heads-up |
| medium | `alerts_medium` | `IMPORTANCE_DEFAULT` | Standard |
| low | `alerts_low` | `IMPORTANCE_LOW` | Silent summary |

The shared module will expose a typed severity enum to keep mapping consistent across platforms.

## 4. Future Push Providers

| Provider | Notes |
|----------|-------|
| Firebase Cloud Messaging | Recommended for Play Store devices; integrate via `com.google.firebase:firebase-messaging` once backend gains push token storage. |
| Huawei Push Kit | Required for Huawei AppGallery builds; the shared module should abstract push registration behind a platform interface. |

## 5. Offline & Retry Strategy

- WebSocket reconnect logic must implement exponential backoff (baseline handled in shared module).
- Alerts received while the app is backgrounded should be persisted (Room database on Android) for badge counts and offline history.
- Upon reconnect, call `/api/alerts?status=active&hours=24` to reconcile missed events.

## 6. Outstanding Decisions

1. Decide whether background services are needed to keep the WebSocket alive while the app is backgrounded for long periods.
2. Determine retention policy for locally cached alerts (default proposal: 7 days).
3. Confirm if server-side quiet hours should mirror mobile local quiet hours.

This document will evolve with implementation details in Phases 2 and 3.
