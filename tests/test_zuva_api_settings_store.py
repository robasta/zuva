"""Settings must be durable.

They used to be read back from InfluxDB with a bounded range, so a restart more
than a day after the last write lost every user's configuration while the
service still reported healthy.
"""
from datetime import datetime, timedelta

import pytest

from zuva_api.models import UserSettings
from zuva_api.settings_store import DEFAULT_DB_PATH, SettingsStore


@pytest.fixture
def store(tmp_path):
    store = SettingsStore(str(tmp_path / "zuva.db"))
    store.initialize()
    return store


def make_settings(**overrides):
    values = {
        "user_id": "u1",
        "enabled_channels": ["telegram"],
        "telegram_chat_id": "chat",
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
        "min_severity": "medium",
        "rate_limit_minutes": 15,
    }
    values.update(overrides)
    return UserSettings(**values)


def test_load_all_is_empty_on_a_fresh_database(store):
    assert store.load_all() == {}


def test_save_then_load(store):
    store.save(make_settings())

    loaded = store.load_all()["u1"]
    assert loaded.enabled_channels == ["telegram"]
    assert loaded.telegram_chat_id == "chat"
    assert loaded.quiet_hours_start == "22:00"
    assert loaded.min_severity == "medium"
    assert loaded.rate_limit_minutes == 15
    assert loaded.last_alert_times == {}


def test_save_upserts_instead_of_duplicating(store):
    store.save(make_settings())
    store.save(make_settings(min_severity="critical", rate_limit_minutes=60))

    loaded = store.load_all()
    assert list(loaded) == ["u1"]
    assert loaded["u1"].min_severity == "critical"
    assert loaded["u1"].rate_limit_minutes == 60


def test_settings_survive_reopening_the_file(tmp_path):
    path = str(tmp_path / "zuva.db")
    first = SettingsStore(path)
    first.initialize()
    first.save(make_settings(telegram_chat_id="chat-1"))

    reopened = SettingsStore(path)
    reopened.initialize()

    assert reopened.load_all()["u1"].telegram_chat_id == "chat-1"


def test_empty_channel_list_round_trips(store):
    store.save(make_settings(enabled_channels=[]))

    assert store.load_all()["u1"].enabled_channels == []


def test_missing_chat_id_round_trips_as_none(store):
    store.save(make_settings(telegram_chat_id=None))

    assert store.load_all()["u1"].telegram_chat_id is None


def test_record_alert_is_loaded_as_rate_limit_state(store):
    store.save(make_settings())
    when = datetime.now() - timedelta(minutes=3)

    store.record_alert("u1", "grid_outage", when)

    assert store.load_all()["u1"].last_alert_times == {"grid_outage": when}


def test_record_alert_keeps_only_the_latest_per_category(store):
    store.save(make_settings())
    older = datetime.now() - timedelta(hours=2)
    newer = datetime.now()

    store.record_alert("u1", "grid_outage", older)
    store.record_alert("u1", "grid_outage", newer)

    assert store.load_all()["u1"].last_alert_times == {"grid_outage": newer}


def test_alert_state_is_tracked_per_category(store):
    store.save(make_settings())
    now = datetime.now()

    store.record_alert("u1", "grid_outage", now)
    store.record_alert("u1", "battery_low", now)

    assert set(store.load_all()["u1"].last_alert_times) == {"grid_outage", "battery_low"}


def test_alert_state_for_unknown_users_is_ignored(store):
    store.save(make_settings())
    store.record_alert("ghost", "grid_outage", datetime.now())

    loaded = store.load_all()
    assert list(loaded) == ["u1"]
    assert loaded["u1"].last_alert_times == {}


def test_unparseable_timestamps_are_skipped(store):
    store.save(make_settings())
    store.record_alert("u1", "grid_outage", datetime.now())
    with store._connect() as conn:
        conn.execute("UPDATE alert_state SET last_sent_at = 'garbage'")

    assert store.load_all()["u1"].last_alert_times == {}


def test_initialize_is_idempotent(store):
    store.save(make_settings())
    store.initialize()

    assert list(store.load_all()) == ["u1"]


def test_path_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SETTINGS_DB_PATH", str(tmp_path / "from-env.db"))
    assert SettingsStore().path == str(tmp_path / "from-env.db")

    monkeypatch.delenv("SETTINGS_DB_PATH")
    # Defaults to a mounted volume so settings survive container recreation.
    assert SettingsStore().path == DEFAULT_DB_PATH
