# Sunsynk Project to SaaS: Production Plan

## Direct Answer
To turn this project into a SaaS, implement it as a multi-tenant platform with three clear services: control plane API, ingestion workers, and notification delivery. The immediate priority is to remove current security blockers, then add tenant-aware identity/data boundaries, then harden reliability and operations.

This plan is ordered to reduce risk quickly while improving ease of use for non-technical customers.

## What Must Change First (P0)

### 1) Security Baseline (Blocker)
1. Enable TLS certificate and hostname verification by default in the Sunsynk client.
2. Make insecure TLS mode local-dev only and explicitly opt-in.
3. Remove hardcoded credentials/tokens from compose and deployment files.
4. Require secrets through environment variables or a secrets manager.
5. Add API authentication for all settings/alerts/admin endpoints.
6. Restrict CORS to approved frontend origins.
7. Add API rate limiting and basic abuse protection.

Why this is first: the current defaults are not safe for internet-exposed SaaS.

### 2) Multi-Tenant Foundation
1. Introduce tenant-aware entities: organization, site, inverter, user, role, integration credential, notification policy.
2. Store identity/configuration in PostgreSQL (system of record).
3. Keep InfluxDB for telemetry/time-series workloads.
4. Propagate tenant context from auth token through API, workers, and persistence.
5. Remove any singleton/default-user runtime behavior.

Why this is first-tier: without tenant isolation, you do not have a SaaS-safe data model.

### 3) Authentication and Access Control
1. Implement OIDC/OAuth2-compatible auth.
2. Add RBAC with tenant-scoped permission checks.
3. Add account lifecycle flows: invite, verify email, password reset, session revoke, API key rotation.
4. Add audit logging for auth and policy changes.

Why this is first-tier: secure self-service access is core to SaaS usability and safety.

## High-Impact Next Changes (P1)

### 4) Reliability and Event Processing
1. Move alert processing to queue-backed workers.
2. Add retries with dead-letter queue.
3. Add idempotency keys/deduplication to prevent duplicate alerts.
4. Add per-tenant throttling/backpressure.
5. Define retention and archival strategy.

### 5) Production Platform and Operations
1. Add infrastructure as code for dev/staging/prod.
2. Add CI/CD with gated promotion, rollback, dependency/security scanning, and SBOM generation.
3. Add observability: metrics, logs, traces, synthetic checks.
4. Define SLOs and alerting thresholds.
5. Create on-call runbooks and incident response workflow.

### 6) Compliance and Governance
1. Define policies for access control, change management, incident response, and vendor risk.
2. Maintain immutable audit trails for privileged actions.
3. Implement backup/restore with tested RPO/RTO.
4. Add data classification, retention, and deletion workflows.

## Ease of Use Requirements (Product + UX)
1. Build a web console (do not rely on API-only onboarding).
2. Provide guided setup: create account, connect Sunsynk credentials, discover devices, set thresholds, test notifications.
3. Provide safe defaults and prebuilt templates for common usage patterns.
4. Provide in-app diagnostics (credential checks, connectivity checks, delivery tests).
5. Publish clear customer docs: quickstart, troubleshooting, and service status.

## Recommended Architecture for This Repository
1. Keep `sunsynk/` as SDK/integration layer with secure defaults.
2. Evolve `zuva_api/` into a control plane API with modules for auth, tenant management, policies, and admin.
3. Evolve `zuva/collector/` into tenant-aware worker services.
4. Add an internal event contract between ingestion and notifications.
5. Keep service boundaries explicit: API (sync), workers (async), storage (relational + time-series).

## Production-Readiness Checklist (Concise)

### Security
- [ ] TLS verification enabled by default across all outbound HTTP clients.
- [ ] No hardcoded secrets in repository or compose files.
- [ ] Secrets sourced from environment/secret manager with rotation policy.
- [ ] Authn/authz enforced on all non-public endpoints.
- [ ] CORS restricted to known origins.
- [ ] Rate limiting and audit logging enabled.

### Multi-Tenancy
- [ ] Tenant-aware schema and authorization checks implemented.
- [ ] Tenant context propagated end-to-end.
- [ ] Cross-tenant access tests passing.

### Reliability
- [ ] Queue-backed processing with retry + dead-letter queue.
- [ ] Idempotency/dedup in alert pipeline.
- [ ] Backups verified and restore drill completed.
- [ ] SLOs defined with alert thresholds.

### Operations
- [ ] IaC for all environments.
- [ ] CI/CD includes tests, security scans, and rollback strategy.
- [ ] Centralized metrics/logs/traces and runbooks in place.

### Ease of Use
- [ ] Guided onboarding in web UI.
- [ ] Notification testing and connection diagnostics in product.
- [ ] Clear docs and support paths available.

## 90-Day Rollout Plan

### Days 1-30: Secure Foundations
1. Complete all P0 security items.
2. Introduce auth and tenant-aware domain model.
3. Remove insecure defaults and hardcoded secrets from deployment paths.
4. Add baseline audit logs and CORS/rate-limiting controls.
5. Deliver migration notes for existing users.

Exit criteria:
1. No critical security findings open.
2. Tenant boundaries enforced in API and persistence paths.

### Days 31-60: Reliability and Internal Beta
1. Implement queue-backed alert processing with retries and DLQ.
2. Add idempotency/dedup and per-tenant limits.
3. Deploy staging with CI/CD gates and observability.
4. Run internal and friendly-customer beta.
5. Start web onboarding flow and diagnostics.

Exit criteria:
1. Alert pipeline stable under load tests.
2. Key SLO dashboards and operational alerts live.

### Days 61-90: Production Launch Readiness
1. Finalize onboarding UX and customer docs.
2. Complete runbooks, incident workflows, and restore drills.
3. Finalize compliance baseline controls and evidence collection.
4. Perform security review and launch readiness review.
5. Launch gradually (small tenant cohort, then expand).

Exit criteria:
1. Launch checklist complete.
2. On-call readiness confirmed.
3. Initial production tenants onboarded with acceptable support load.

## Key Risks and Mitigations
1. Upstream Sunsynk API instability.
Mitigation: retries, backoff, circuit breakers, and customer-visible status.
2. Duplicate or missed alerts during restarts.
Mitigation: idempotency keys, durable queues, replay-safe worker design.
3. Security regressions during rapid delivery.
Mitigation: CI security gates, threat modeling for P0/P1 changes, staged rollout.

## Decision Points to Confirm Early
1. Target customer type: residential, installer, enterprise, or mixed.
2. Cloud/provider strategy and managed services constraints.
3. Compliance target in year 1 (baseline controls only vs SOC 2 roadmap).
