# Proposal: Learning Alarm Thresholds From Historical Usage

**Status: proposal, not implemented.** Nothing below exists in the code yet.

Scope note: the product is notifications. There is no dashboard and no frontend
app, so anything learned here has to arrive as a Telegram message or change which
messages get sent - not as a chart for someone to read.

## 1) What exists today

- Alerting is rule-based, with static thresholds and fixed time windows in
  `zuva/collector/alert_logic.py`.
- Consumption checks are hard-coded by time of day: silent 05:00-18:00, an
  evening threshold 18:00-22:00, and a night threshold otherwise.
- The notification service (`zuva_api/notification_service.py`) already handles
  severity filtering, quiet hours, per-category rate limiting, and recording what
  was sent.
- Poll readings are stored: the collector posts each poll to `POST /telemetry`
  and `zuva-api` writes a row to the `readings` table in `/data/zuva.db`
  (`inverter_sn`, `plant_id`, `load_power_w`, `grid_power_w`, `battery_soc`,
  `grid_voltage`, `grid_status`, `battery_power_w`, `battery_voltage`,
  `input_power_w`, `recorded_at` as UTC ISO-8601).

So the historical series this proposal needs already accumulates. Two caveats
before relying on it:

- `HISTORY_RETENTION_DAYS` defaults to 90, which is enough for an 8-week training
  window but not much more. A longer window means raising it.
- At the default `POLL_INTERVAL` of 600s there are ~144 rows per inverter per
  day, so a `(weekday, hour)` slot gets ~6 samples per day of history.

## 2) Recommended approach: adaptive thresholds per time slot

Build a baseline profile per `(weekday, hour)` (or 30-minute bin) from the last
6-8 weeks, then alert when a live reading is abnormal *for that slot* rather than
against one global number.

### 2.1 Baseline model

Per slot, over the training window:

- `p50` (median), `p90` (normal high bound), `mad` (median absolute deviation).
- `warning = max(p90 * 1.15, p50 + 3 * mad)`
- `critical = max(p90 * 1.35, p50 + 5 * mad)`

Then clamp: a floor so noise cannot alert, and a ceiling so a bad training window
cannot silence everything.

Median/MAD rather than mean/stddev because a single grid outage or a pool pump
left on overnight should not move the baseline.

### 2.2 Live detection

Inside the poll loop:

1. Determine the current `(weekday, slot)`.
2. Load that slot's learned thresholds.
3. Compare the current `load_power_w`.
4. Require `N` consecutive breaches (2-3) before firing, as grid outages already
   do.
5. Leave rate limiting and quiet hours to `zuva-api` - they already work.

Behaviour this produces: if weekday 04:00-05:00 has historically run at ~2.0 kW,
that is learned as normal instead of tripping the night threshold every morning;
if 16:00-18:00 normally sits at ~0.4 kW, a 0.7 kW reading there becomes worth a
message.

## 3) Threshold tuning as a notification

A daily job (say 06:00) summarises what it learned and sends it as one Telegram
message under a new `insight_report` category - a digest the owner reads once a
day, not a dashboard:

- top high-usage slots by weekday,
- recurring spikes (for example every weekday 04:00-05:00),
- slots where the current static thresholds are too strict or too loose,
- recommended threshold updates, with sample size and confidence.

For example:

- `Mon-Fri 04:00-05:00: expected 2.0kW, warning 2.4kW, confidence high (n=42 days)`
- `Mon-Fri 16:00-18:00: expected 0.4kW, warning 0.55kW, confidence high (n=41 days)`

## 4) Storage additions

Two tables alongside the existing `readings`, in the same `/data/zuva.db`:

1. `alarm_profiles` - `inverter_sn`, `weekday`, `slot`, `p50`, `p90`, `mad`,
   `warning_threshold`, `critical_threshold`, `sample_count`, `updated_at`;
   primary key `(inverter_sn, weekday, slot)`.
2. `alarm_events` - `inverter_sn`, `severity`, `weekday`, `slot`, `actual_w`,
   `threshold_w`, `deviation_pct`, `profile_version`, `recorded_at`; the record of
   why an adaptive alert fired, so a bad profile can be diagnosed after the fact.

Both need to be exempt from, or given a longer window than,
`HISTORY_RETENTION_DAYS` - a profile is not telemetry.

## 5) Integration plan

Profiles are computed where the data lives, which is `zuva_api`, not the
collector. The collector reads them over the API it already authenticates to.

### Phase 1: suggestion only

- Add `zuva_api/alarm_profiles.py`: query `readings`, compute per-slot
  statistics, persist profiles, and produce the daily digest.
- Expose `GET /alarm-profiles/{inverter_sn}` behind the existing `X-API-Key`.
- Keep the static checks exactly as they are; only send the digest.

### Phase 2: runtime adaptive alerts

- Extend `check_consumption_alerts` to prefer an adaptive threshold when a
  profile exists for the current slot, and fall back to the static one when it
  does not.
- Cache profiles in the collector and refresh them daily; a poll must not depend
  on a second HTTP call succeeding.

### Phase 3: confidence and safety

- Activate a slot only once `sample_count >= min_samples` (14-21 days).
- Confirm with consecutive breaches.
- Cap adaptive alerts per slot per day, so a broken profile cannot become a
  message flood.

## 6) Why this approach

- Explainable: a person can read the profile and see why an alert fired.
- Robust to outliers, being median/MAD based.
- Works with limited data and needs no ML infrastructure - the whole thing is
  SQL plus `statistics` from the standard library.
- It answers the actual requirement: learn what normal looks like per weekday and
  time, without hand-defining every threshold.

## 7) Decisions to lock in before coding

1. Slot granularity: 60 min vs 30 min.
2. Training window: 6 vs 8 weeks - and whether to raise
   `HISTORY_RETENTION_DAYS` to match.
3. Minimum sample count for confidence.
4. Reuse the `high_consumption` category or add `adaptive_consumption`
   (a new category means editing the `AlertCategory` enum in `zuva_api/models.py`).
5. How long to stay in suggestion-only mode before enabling auto-trigger.
