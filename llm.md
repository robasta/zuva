# Findings: Learning Alarms From Historical Solar Usage Data

## 1) What exists today

- The current alerting logic is rule-based with static thresholds and fixed time windows in `zuva/collector/alert_monitor.py`.
- Existing consumption checks are currently hard-coded by time of day, for example:
	- 18:00-22:00 uses a fixed evening threshold.
	- 22:00-05:00 uses a fixed night threshold.
- The notification service (`zuva_api/main.py`) already handles:
	- severity filtering,
	- quiet hours,
	- rate-limiting,
	- persistence of sent alerts.

## 2) Important gap to solve first

- In this repository, the usage/telemetry writes are not currently visible (alerts and user settings are persisted, but load usage writes are not shown).
- To learn dynamic alarms, we need historical time series for at least:
	- timestamp,
	- load power (W or kW),
	- inverter identifier,
	- optional context (weekday/weekend, battery SOC, grid status).

If usage data is already being written from another process/environment, we can start immediately using that bucket/measurement. If not, add telemetry writes in the collector first.

## 3) Recommended solution: Adaptive Alarm Engine

Use historical data to build a baseline profile by day-of-week and time window, then trigger alerts when live readings exceed learned expected ranges.

### 3.1 Baseline model (simple, robust)

For each slot `(weekday, hour)` (or `(weekday, 30-minute bin)`):

- Collect the last 6-8 weeks of readings.
- Compute robust statistics:
	- `p50` (median),
	- `p90` (normal high bound),
	- `mad` (median absolute deviation) for noise robustness.
- Learn two thresholds per slot:
	- warning threshold,
	- critical threshold.

Recommended formulas:

- `warning = max(p90 * 1.15, p50 + 3 * mad)`
- `critical = max(p90 * 1.35, p50 + 5 * mad)`

Then clamp with safety limits:

- minimum threshold floor to avoid tiny-noise alerts,
- maximum threshold ceiling to avoid runaway values.

### 3.2 Live detection logic

At runtime (inside monitor loop):

1. Determine current `(weekday, slot)`.
2. Load the learned baseline thresholds for that slot.
3. Compare current `load_power` to `warning` and `critical`.
4. Require `N` consecutive breaches (for example `N=2` or `N=3`) before firing.
5. Keep cooldown/rate limits (already supported by notification service).

This gives behavior like:

- If weekdays 04:00-05:00 are historically around 2.0 kW, the system learns that as expected and can notify only when abnormal relative to that slot.
- If 16:00-18:00 are historically around 0.4 kW, the learned threshold might become around 0.5-0.7 kW, and alerts fire automatically above that range.

## 4) Auto-generated insights for alarm tuning

Add a daily insights job (for example at 06:00) that summarizes:

- top high-usage slots by weekday,
- recurring spikes (for example every weekday 04:00-05:00),
- slots where current static alarms are too strict or too loose,
- recommended threshold updates.

Output format should include confidence and sample size, for example:

- `weekday=Mon-Fri, slot=04:00-05:00, expected=2.0kW, warning=2.4kW, confidence=high (n=42 days)`
- `weekday=Mon-Fri, slot=16:00-18:00, expected=0.4kW, warning=0.55kW, confidence=high (n=41 days)`

This can be sent as:

- notification alert category (insight report),
- and/or API endpoint for dashboard consumption.

## 5) Data model additions

Recommended measurements/tables:

1. `usage_readings`
- tags: `inverter_sn`, `plant_id`
- fields: `load_power_kw`, `grid_power_kw`, `battery_soc`, `grid_voltage`
- time: ingestion timestamp

2. `adaptive_alarm_profiles`
- tags: `inverter_sn`, `weekday`, `slot`
- fields: `p50`, `p90`, `mad`, `warning_threshold`, `critical_threshold`, `sample_count`, `updated_at`

3. `adaptive_alarm_events`
- tags: `inverter_sn`, `severity`, `slot`, `weekday`
- fields: `actual_kw`, `threshold_kw`, `deviation_pct`, `profile_version`

## 6) Integration plan for this codebase

### Phase 1: baseline and recommendations

- Add a new module (example: `zuva/collector/adaptive_alarms.py`) to:
	- query historical usage,
	- compute per-slot thresholds,
	- persist profiles,
	- generate recommendation summaries.
- Keep existing static checks as fallback.

### Phase 2: runtime adaptive alerts

- Extend `check_consumption_alerts` to:
	- prefer adaptive thresholds when profile exists,
	- fallback to static thresholds when profile missing.
- Keep existing rate limiting and quiet-hour controls.

### Phase 3: confidence and safety

- Only activate adaptive threshold for a slot when `sample_count >= min_samples` (for example 14-21 days).
- Add anomaly confirmation using consecutive breaches.
- Add a max alerts per slot/day guard.

## 7) Why this approach is a good fit

- It is explainable (easy to reason about and tune).
- It is robust to outliers (median/MAD based).
- It works with limited data and does not require heavy ML infrastructure.
- It directly answers your requirement: auto-learn thresholds by weekday/time and trigger warnings without manually defining each alarm.

## 8) Next implementation details to lock in

Before coding, decide:

1. Slot granularity: 60 min vs 30 min.
2. Training window: 6 vs 8 weeks.
3. Minimum confidence sample count.
4. Whether adaptive alerts should use existing `high_consumption` category or a new category (for example `adaptive_consumption`).
5. Whether to run in suggestion-only mode first, then auto-trigger mode.

## 9) Minimal Flux query pattern (example)

Use this pattern to fetch historical usage by slot:

```flux
from(bucket: "solar_data")
	|> range(start: -8w)
	|> filter(fn: (r) => r._measurement == "usage_readings")
	|> filter(fn: (r) => r._field == "load_power_kw")
	|> map(fn: (r) => ({
			r with
			weekday: string(v: date.weekDay(t: r._time)),
			hour: date.hour(t: r._time)
	}))
```

Then compute percentile and MAD per `(weekday, hour)` in Python, store results in `adaptive_alarm_profiles`, and read those profiles in the live monitor path.
