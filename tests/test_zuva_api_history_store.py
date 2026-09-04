"""Tests for the alert and telemetry history that replaced InfluxDB.

The two properties worth pinning: a lookup only returns the asked-for user's
alerts inside the asked-for window, and something deletes old rows - the bucket
retention used to do that, and nothing else does now.
"""
from datetime import timedelta

import pytest

from zuva_api.history_store import HistoryStore
from zuva_api.timeutil import local_now


@pytest.fixture
def store(tmp_path):
    store = HistoryStore(str(tmp_path / "zuva.db"))
    store.initialize()
    return store


def test_recorded_alert_comes_back_with_local_time(store):
    sent_at = local_now()
    store.record_alert("u1", "grid_outage", "high", "Grid", "Down", when=sent_at)

    alerts = store.recent_alerts("u1", hours=1)

    assert len(alerts) == 1
    assert alerts[0]["category"] == "grid_outage"
    assert alerts[0]["severity"] == "high"
    assert alerts[0]["title"] == "Grid"
    assert alerts[0]["message"] == "Down"
    # Stored as UTC, handed back in the configured zone.
    assert alerts[0]["time"].utcoffset() == sent_at.utcoffset()
    assert abs((alerts[0]["time"] - sent_at).total_seconds()) < 1


def test_history_is_scoped_to_the_user(store):
    store.record_alert("u1", "grid_outage", "high", "Mine", "m")
    store.record_alert("u2", "grid_outage", "high", "Theirs", "t")

    assert [a["title"] for a in store.recent_alerts("u1", hours=1)] == ["Mine"]


def test_history_is_bounded_by_the_window(store):
    now = local_now()
    store.record_alert("u1", "grid_outage", "high", "Old", "o", when=now - timedelta(hours=5))
    store.record_alert("u1", "grid_outage", "high", "Recent", "r", when=now - timedelta(minutes=5))

    assert [a["title"] for a in store.recent_alerts("u1", hours=1)] == ["Recent"]


def test_history_is_newest_first(store):
    now = local_now()
    store.record_alert("u1", "battery_low", "medium", "First", "f", when=now - timedelta(hours=2))
    store.record_alert("u1", "battery_low", "medium", "Second", "s", when=now - timedelta(hours=1))

    assert [a["title"] for a in store.recent_alerts("u1", hours=6)] == ["Second", "First"]


def test_user_id_is_bound_as_a_parameter(store):
    """The user id is data, never concatenated into SQL."""
    store.record_alert("u1", "grid_outage", "high", "Mine", "m")

    assert store.recent_alerts("u1' OR '1'='1", hours=1) == []
    # And the table is still there afterwards.
    assert len(store.recent_alerts("u1", hours=1)) == 1


def test_reading_round_trips_every_column(store):
    store.record_reading(
        inverter_sn="SN1",
        plant_id="7",
        load_power_w=812.0,
        grid_power_w=-45.0,
        battery_soc=64.0,
        grid_voltage=230.1,
        grid_status=1,
        battery_power_w=-1.2,
        battery_voltage=52.4,
        input_power_w=4.7,
    )

    with store._connect() as conn:
        row = conn.execute("SELECT * FROM readings").fetchone()

    assert row["inverter_sn"] == "SN1"
    assert row["load_power_w"] == 812.0
    assert row["grid_status"] == 1
    assert row["input_power_w"] == 4.7


def test_reading_accepts_only_the_required_fields(store):
    store.record_reading(
        inverter_sn="SN1", load_power_w=1.0, grid_power_w=2.0, battery_soc=3.0
    )

    with store._connect() as conn:
        row = conn.execute("SELECT * FROM readings").fetchone()

    assert row["grid_voltage"] is None


def test_unknown_reading_field_is_rejected(store):
    """A typo must fail loudly rather than being silently dropped."""
    with pytest.raises(ValueError, match="unknown reading fields"):
        store.record_reading(
            inverter_sn="SN1",
            load_power_w=1.0,
            grid_power_w=2.0,
            battery_soc=3.0,
            solar_power_kw=9.0,
        )


def test_prune_deletes_rows_past_the_retention_window(store):
    old = local_now() - timedelta(days=120)
    store.record_reading(recorded_at=old, inverter_sn="SN1", load_power_w=1.0,
                         grid_power_w=0.0, battery_soc=50.0)
    store.record_reading(inverter_sn="SN1", load_power_w=2.0,
                         grid_power_w=0.0, battery_soc=51.0)
    store.record_alert("u1", "grid_outage", "high", "Old", "o", when=old)
    store.record_alert("u1", "grid_outage", "high", "New", "n")

    store.prune(retention_days=90)

    with store._connect() as conn:
        readings = conn.execute("SELECT COUNT(*) AS n FROM readings").fetchone()["n"]
    assert readings == 1
    assert [a["title"] for a in store.recent_alerts("u1", hours=8760)] == ["New"]


def test_retention_of_zero_days_keeps_everything(store):
    """Otherwise a misconfigured 0 would wipe the table on the next write."""
    store.record_reading(recorded_at=local_now() - timedelta(days=900), inverter_sn="SN1",
                         load_power_w=1.0, grid_power_w=0.0, battery_soc=50.0)

    assert store.prune(retention_days=0) == 0

    with store._connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM readings").fetchone()["n"] == 1


def test_writes_prune_periodically_not_on_every_row(store, monkeypatch):
    prunes = []
    monkeypatch.setattr(store, "prune", lambda: prunes.append(1))

    store._last_prune = None
    store.record_reading(inverter_sn="SN1", load_power_w=1.0, grid_power_w=0.0, battery_soc=1.0)
    store._last_prune = 10 ** 9  # far in the future of any real monotonic reading
    store.record_reading(inverter_sn="SN1", load_power_w=1.0, grid_power_w=0.0, battery_soc=1.0)

    assert len(prunes) == 1


def test_a_failed_prune_does_not_lose_the_reading(store, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "prune", boom)

    store.record_reading(inverter_sn="SN1", load_power_w=5.0, grid_power_w=0.0, battery_soc=1.0)

    with store._connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM readings").fetchone()["n"] == 1


def test_stores_share_one_database_file(tmp_path, monkeypatch):
    """One volume, one backup: settings and history live in the same file."""
    from zuva_api.settings_store import SettingsStore

    monkeypatch.setenv("SETTINGS_DB_PATH", str(tmp_path / "zuva.db"))
    settings_store = SettingsStore()
    history_store = HistoryStore()
    settings_store.initialize()
    history_store.initialize()

    assert settings_store.path == history_store.path

    history_store.record_alert("u1", "grid_outage", "high", "T", "m")
    with history_store._connect() as conn:
        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
    assert {"user_settings", "alert_state", "alerts", "readings"} <= tables
