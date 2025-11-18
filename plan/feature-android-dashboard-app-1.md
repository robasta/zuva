---
goal: Android Mobile App for Sunsynk Dashboard
version: 1.0
date_created: 2025-11-18
owner: Mobile Platform Team
status: Planned
tags: [feature, mobile, android, notifications, multiplatform]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Design and implement an Android application that mirrors the Sunsynk dashboard feature set, integrates with the existing backend and notification subsystems, and establishes a foundation for future iOS and Huawei builds through reusable shared modules.

## 1. Requirements & Constraints

- **REQ-001**: Deliver feature parity with the existing web dashboard (current metrics, history, timeseries, alerts, settings, analytics views).
- **REQ-002**: Consume existing REST and WebSocket endpoints under `/api` and `/ws/dashboard` with OAuth2 bearer auth identical to the web client.
- **REQ-003**: Provide in-app alerting via existing WebSocket push plus local notifications; leverage placeholders for email/SMS hooks already present in backend.
- **REQ-004**: Support offline caching for last-known metrics and alert history for at least 24 hours.
- **REQ-005**: Implement secure credential storage using Android Keystore-backed encrypted preferences.
- **SEC-001**: Enforce JWT storage protections and prevent logging of secrets per security guidance.
- **INT-001**: Reuse shared business logic for prospective iOS/Huawei deployments using Kotlin Multiplatform shared modules.
- **UX-001**: Adhere to Material 3 design guidelines with dark/light themes aligned with web branding.
- **CON-001**: Maintain compatibility with Android 10 (API 29) and newer devices.
- **CON-002**: Continue to rely on existing backend notification infrastructure (WebSocket broadcast confirmed in `sunsynk-dashboard/backend/main.py::_send_push_notification`).
- **GUD-001**: Use Jetpack Compose for UI to align with modern Android practices.
- **PAT-001**: Adopt MVVM with Repository pattern and Kotlin Coroutines/Flows for data streams.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Establish shared architecture, confirm backend integration points, and scaffold Android project with multiplatform-ready modules.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Audit backend endpoints (`/api/dashboard/*`, `/api/v6/*`, `/api/alerts/*`, `/ws/dashboard`) and document payload contracts in `docs/mobile/backend-contract.md`. |  |  |
| TASK-002 | Verify notification pipeline (WebSocket broadcast plus alert stubs) and define mobile notification handling spec in `docs/mobile/notifications.md`. |  |  |
| TASK-003 | Generate Android Studio project using Kotlin Multiplatform template with shared `:shared` module and Android `:app` module under `mobile/android`. |  |  |
| TASK-004 | Configure KMP shared module to host API clients (Ktor), auth manager, DTOs mirroring existing TypeScript interfaces, and multiplatform serialization. |  |  |
| TASK-005 | Set up dependency injection (Koin or Hilt for Android + Koin for shared code) and write baseline unit tests validating API deserialization. |  |  |

### Implementation Phase 2

- GOAL-002: Implement core Android features, Compose UI, and local notification handling with reusable shared logic.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Build authentication flow (login screen, token storage via `EncryptedSharedPreferences`, session refresh) consuming shared auth repository. |  |  |
| TASK-007 | Implement dashboard screens (current metrics, timeseries chart, historical list) using Compose; bind to shared repositories with Flow-based view models. |  |  |
| TASK-008 | Add alert center (active/resolved list, detail view) using WebSocket listener in shared layer and Room-based local cache. |  |  |
| TASK-009 | Integrate Android NotificationManager to display push-style alerts triggered from WebSocket events; map severity to channels. |  |  |
| TASK-010 | Implement settings screens backed by shared settings repository hitting `/api/settings/*` endpoints with optimistic updates and error handling. |  |  |
| TASK-011 | Wire analytics (consumption patterns, battery optimization, forecasting) views using paged data and Compose navigation. |  |  |

### Implementation Phase 3

- GOAL-003: Harden app for production, add offline support, QA, and document multiplatform extension strategy.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Implement offline caching (Room + shared repository cache) for metrics/alerts with 24-hour retention and sync conflict resolution. |  |  |
| TASK-013 | Build instrumentation tests (Espresso/Compose testing) and shared unit tests to cover networking, caching, and alert workflows. |  |  |
| TASK-014 | Profile WebSocket handling under poor connectivity; add exponential backoff and foreground service guard for long-lived connections. |  |  |
| TASK-015 | Create multiplatform rollout guide in `docs/mobile/multiplatform-strategy.md` covering iOS/Huawei targets, KMP module reuse, and Flutter/Compose evaluation. |  |  |
| TASK-016 | Prepare release assets (Play Store listing, signed bundles) and document CI/CD pipeline (GitHub Actions) for build/test/deploy. |  |  |

## 3. Alternatives

- **ALT-001**: Flutter single codebase (per https://flutter.dev/multi-platform) offering shared UI for Android/iOS/Huawei; rejected due to existing Kotlin expertise and need for deep Android integration.
- **ALT-002**: React Native leveraging existing TypeScript logic; rejected because notification/websocket stack would require substantial adaptation and less native performance.
- **ALT-003**: Native-only Android without shared module; rejected to preserve path toward iOS/Huawei reuse.

## 4. Dependencies

- **DEP-001**: Kotlin Multiplatform toolchain (per Google KMP guidance https://developer.android.com/kotlin/multiplatform) and Android Studio Koala+.
- **DEP-002**: Backend endpoints stability; requires coordination with backend team for any schema changes.
- **DEP-003**: Firebase Cloud Messaging (optional) or Huawei Push Kit for future push escalation (design placeholder).

## 5. Files

- **FILE-001**: `docs/mobile/backend-contract.md` — Endpoint contracts, payload samples.
- **FILE-002**: `docs/mobile/notifications.md` — Mobile notification architecture and mapping to backend channels.
- **FILE-003**: `docs/mobile/multiplatform-strategy.md` — Shared module reuse strategy for Android/iOS/Huawei.
- **FILE-004**: `mobile/android/app/src/main/...` — Android-specific Compose UI and platform glue code.
- **FILE-005**: `mobile/shared/src/commonMain/...` — Shared business logic, repositories, DTOs.

## 6. Testing

- **TEST-001**: Shared module unit tests covering API client serialization, auth flow, and repository caching using Ktor MockEngine.
- **TEST-002**: Android instrumented tests for Compose navigation, alert notifications, and offline cache fallback using Robolectric/Compose testing.
- **TEST-003**: End-to-end manual regression with backend staging: login, real-time alerts, analytics fetch, settings updates, background WebSocket reconnection.

## 7. Risks & Assumptions

- **RISK-001**: WebSocket reliability on mobile background execution; mitigated through foreground service and reconnect logic.
- **RISK-002**: Backend schema changes breaking shared DTOs; mitigated by contract tests and version pinning.
- **RISK-003**: KMP learning curve delaying delivery; mitigated by starting with shared business logic only and deferring shared UI.
- **ASSUMPTION-001**: Existing notification stubs (email/SMS) remain inactive; mobile relies on WebSocket plus local notifications initially.
- **ASSUMPTION-002**: Future iOS/Huawei teams will adopt shared KMP module; documentation will guide integration.

## 8. Related Specifications / Further Reading

- [Kotlin Multiplatform official guidance](https://developer.android.com/kotlin/multiplatform)
- [Flutter multi-platform overview](https://flutter.dev/multi-platform)
- [Existing dashboard feature specs](feature-dashboard-system-1.md)