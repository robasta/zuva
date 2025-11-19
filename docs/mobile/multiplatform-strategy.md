# Multiplatform Rollout Strategy

## Overview
The Kotlin Multiplatform (KMP) shared module delivers networking, authentication, caching, and domain models for the Sunsynk dashboard experiences. Android consumes the shared module directly today; iOS and Huawei will reuse the same APIs while providing their own native UI layers.

## Shared Module Scope
- Networking: Ktor client with REST + WebSocket support, auth headers, and retry policy.
- Data models: Kotlinx serialization DTOs aligned with backend contracts.
- Repositories: Business logic, offline caching hooks, and alert workflows.
- Dependency injection: Koin modules that can be adopted on all targets.

## Target Platforms
1. **Android** (current): Compose UI, Room-backed cache, Koin.
2. **iOS** (planned): SwiftUI client consuming shared module as XCFramework; Koin replaced with native dependency graph at integration boundary.
3. **Huawei** (planned): HarmonyOS app using ArkUI; shared module compiled via KMP for OpenHarmony runtime with alternate notification plumbing.

## Rollout Plan
1. **Phase A – Stabilize Shared APIs**
   - Freeze repository interfaces and DTOs.
   - Add contract tests to guard payload compatibility.
2. **Phase B – iOS Integration**
   - Export shared module as static framework.
   - Provide Swift-friendly facades (suspend wrappers, Flow to Combine bridges).
   - Build SwiftUI prototype for dashboard + alerts leveraging cached data.
3. **Phase C – Huawei Integration**
   - Validate KMP tooling for HarmonyOS (OpenHarmony plugin).
   - Replace Android-specific dependencies (Room, NotificationManager) with conditional implementations.
   - Implement push bridge (HMS Push Kit) mapped to shared alert notifier API.

## Repository & UI Separation
- Shared repositories expose only platform-agnostic result models (`ApiResult`).
- Platform modules implement `DashboardCache` and notification interfaces.
- UI layers observe Flow/StateFlow streams and translate `fromCache` metadata into offline indicators.

## Testing Strategy
- Shared: Multiplatform unit tests via Ktor MockEngine and coroutine test utilities.
- Android: JVM tests (Robolectric/Compose) plus instrumentation coverage for notifications.
- iOS: XCTest coverage for Swift wrappers and offline cache behavior.

## CI/CD Considerations
- Configure GitHub Actions matrix build (`android`, `ios`, `shared`).
- Enforce API compatibility by generating Swift header diffs per commit.
- Publish shared module artifacts to internal Maven + binary XCFramework to SPM feed.
