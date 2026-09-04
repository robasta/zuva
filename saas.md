# Proposal: Sunsynk Project to Multi-Tenant SaaS

**Status: proposal, not implemented.** The current stack is two containers serving
one household. Nothing below is a description of existing code.

## Scope

The product is notifications: something watches an inverter and sends a Telegram
message when it matters. There is no dashboard, no web console and no frontend
app, and this plan does not add one. That removes most of what usually makes a
SaaS expensive - onboarding UI, charting, session management in a browser - and
leaves a narrower question: how do you run the notification pipeline for many
households instead of one?

Everything below is ordered so the risky parts come first.

## Already done

These were P0 items in an earlier draft and are now in the code:

- TLS certificate and hostname verification is on by default in
  `sunsynk/client.py`; `verify_tls=False` / `SUNSYNK_VERIFY_TLS=false` is
  explicitly documented as lab-only.
- No hardcoded secrets in the deployment path.
  `scripts/deploy/docker-compose.prod.yml` fails the deploy with a named message
  when a secret is missing rather than falling back to a well-known value.
- Every endpoint except `/health` requires `X-API-Key` with a constant-time
  compare, and `zuva_api` refuses to start when `ZUVA_API_KEY` is unset, so it
  cannot come up unauthenticated.
- Storage is one SQLite file owned by `zuva-api`. The collector holds no database
  credentials at all; it posts alerts and telemetry over the authenticated API.
- Alert suppression state is persisted, so a restart does not re-send every alert.
- `CORS_ORIGINS` defaults to empty, because nothing in a browser calls this API.
  If that stays true, CORS is a non-issue rather than a control to configure.

## What must change first (P0)

### 1) Multi-tenant foundation

1. Introduce tenant-aware entities: account, site, inverter, integration
   credential, notification policy.
2. Move the system of record to PostgreSQL. SQLite is the right call for one
   household on one host; it is the wrong call the moment two API replicas need
   the same rows.
3. Keep readings in the same relational store until volume proves otherwise -
   at a 600s poll interval one inverter produces ~144 rows a day, and a
   time-series database is not warranted by that. Revisit only with numbers.
4. Propagate tenant context from the auth token through the API and the workers.
5. Remove the `DEFAULT_USER_ID` singleton behaviour, which silently files
   everything under one owner.

Without tenant isolation there is no SaaS-safe data model, so this gates
everything else.

### 2) Per-tenant credentials and secrets

1. Each tenant supplies their own Sunsynk credentials; these are the most
   sensitive data in the system and must be encrypted at rest with a key from a
   secrets manager, not stored as plaintext columns.
2. Rotate and revoke per-tenant API keys without redeploying.
3. Audit-log every read of a stored credential.

### 3) Authentication and access control

1. OIDC/OAuth2-compatible auth for the API - a single shared static key does not
   generalise past one tenant.
2. Tenant-scoped authorization checks on every handler, with cross-tenant access
   tests in CI.
3. Account lifecycle: invite, verify, revoke, API-key rotation. These can be
   API-and-email flows; no UI is required for them.
4. Audit logging for auth and policy changes.

## High-impact next changes (P1)

### 4) Reliability of the alert pipeline

1. One poll loop per tenant does not scale in a single process: move polling to
   queue-backed workers with a per-tenant schedule.
2. Retries with a dead-letter queue for delivery failures.
3. Idempotency keys so a restart mid-delivery cannot double-send.
4. Per-tenant throttling, so one household's outage storm cannot delay everyone
   else's alerts.
5. Respect Sunsynk's own rate limits centrally. Repeated failed logins already
   provoke a verification-code lockout for a single account; doing it across
   hundreds of accounts from one egress IP is a different class of problem.

### 5) Platform and operations

1. Infrastructure as code for dev/staging/prod.
2. CI/CD with gated promotion, rollback, dependency and container scanning, SBOM.
3. Observability: metrics, logs, traces. The heartbeat healthcheck catches a
   wedged poll loop for one process; with workers, "did this tenant get polled in
   the last interval" becomes the metric that matters.
4. Alerting on the alerting: a silent notification pipeline looks exactly like a
   quiet solar system, so absence of delivery has to page someone.
5. Runbooks and an incident workflow.

### 6) Compliance and governance

1. Policies for access control, change management, incident response, vendor risk.
2. Immutable audit trails for privileged actions.
3. Backup and restore with a tested RPO/RTO. Today the backup is one Docker
   volume; that does not survive being a business.
4. Data classification, retention and deletion workflows - including deleting a
   tenant's readings and stored Sunsynk credentials on request.

## Ease of use, without a frontend

Onboarding has to be possible for a non-technical owner even though there is no
web console:

1. A guided setup script or a conversational Telegram flow: connect credentials,
   discover inverters, set thresholds, send a test alert.
2. Safe defaults and templates, so a new tenant gets useful alerts without tuning
   anything.
3. Self-diagnostics delivered as messages: credential check, connectivity check,
   delivery test - the questions the troubleshooting section of the README
   currently answers by hand.
4. Customer docs: quickstart, troubleshooting, service status.

If a UI is ever wanted, it should be additive, and the API should not be
restructured in anticipation of one.

## Recommended shape for this repository

1. Keep `sunsynk/` as the integration SDK with secure defaults. It already has no
   dependency on the rest of the repo; keep it that way.
2. Evolve `zuva_api/` into a control plane: auth, tenants, policies, admin.
3. Evolve `zuva/collector/` into tenant-aware workers.
4. Define an explicit event contract between ingestion and notification instead of
   the current direct HTTP post.
5. Keep the boundaries: API is synchronous, workers are asynchronous, storage is
   owned by exactly one service.

## Readiness checklist

### Security
- [ ] Per-tenant Sunsynk credentials encrypted at rest with managed keys.
- [ ] Authn/authz enforced and tenant-scoped on all non-public endpoints.
- [ ] Rate limiting and audit logging enabled.
- [ ] Secrets sourced from a secret manager with a rotation policy.

### Multi-tenancy
- [ ] Tenant-aware schema and authorization checks.
- [ ] Tenant context propagated end to end.
- [ ] Cross-tenant access tests passing in CI.

### Reliability
- [ ] Queue-backed polling and delivery with retry and DLQ.
- [ ] Idempotency in the alert pipeline.
- [ ] Backups verified and a restore drill completed.
- [ ] Missing-delivery detection pages on-call.

### Operations
- [ ] IaC for all environments.
- [ ] CI/CD with tests, security scans and a rollback path.
- [ ] Centralised metrics/logs/traces and runbooks.

### Ease of use
- [ ] Guided onboarding without a UI.
- [ ] In-product diagnostics and a test-notification path.
- [ ] Docs and a support path.

## 90-day rollout

### Days 1-30: tenancy and identity
1. Tenant-aware domain model on PostgreSQL, with a migration path off SQLite.
2. Real auth, replacing the shared static key.
3. Encrypted per-tenant Sunsynk credentials.
4. Audit logs.

Exit criteria: tenant boundaries enforced in both API and persistence, with
cross-tenant tests green.

### Days 31-60: reliability and internal beta
1. Queue-backed polling and delivery with retries and a DLQ.
2. Idempotency and per-tenant limits.
3. Staging with CI/CD gates and observability.
4. Internal and friendly-customer beta.

Exit criteria: the pipeline is stable under load, and a dropped notification is
detectable.

### Days 61-90: launch readiness
1. Onboarding flow and customer docs finished.
2. Runbooks, incident workflow, restore drill.
3. Security review and launch readiness review.
4. Gradual launch: a small cohort, then expand.

Exit criteria: launch checklist complete, on-call confirmed, first tenants running
at an acceptable support load.

## Key risks

1. **Upstream Sunsynk API instability or rate limiting at scale.** Retries,
   backoff, circuit breakers, centralised login throttling, and a customer-visible
   status page.
2. **Duplicate or missed alerts across restarts.** Idempotency keys, durable
   queues, replay-safe workers.
3. **Silent failure.** The failure mode of a notification product is nothing
   happening, which is indistinguishable from good news. Monitor delivery volume
   per tenant, not just process health.
4. **Custody of other people's inverter credentials.** This is the liability that
   makes this a different business from a hobby stack; it deserves a threat model
   of its own before the first external tenant.

## Decisions to confirm early

1. Target customer: residential, installer, enterprise, or mixed.
2. Cloud provider and how much managed infrastructure to lean on.
3. Compliance target in year one: baseline controls only, or a SOC 2 roadmap.
4. Whether Telegram stays the only channel. A second channel changes the delivery
   abstraction, and it is cheaper to decide now than to retrofit.
