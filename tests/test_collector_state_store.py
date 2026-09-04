import json

from zuva.collector.state_store import DEFAULT_STATE_PATH, StateStore


def test_load_returns_empty_when_the_file_is_absent(tmp_path):
    assert StateStore(str(tmp_path / "missing.json")).load() == {}


def test_save_then_load_round_trip(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))

    store.save({"last_battery_alert": "critical", "grid_outage_blocked": True})

    assert store.load() == {"last_battery_alert": "critical", "grid_outage_blocked": True}


def test_save_creates_missing_directories(tmp_path):
    store = StateStore(str(tmp_path / "nested" / "dir" / "state.json"))

    store.save({"a": 1})

    assert store.load() == {"a": 1}


def test_save_is_atomic_and_leaves_no_temp_files(tmp_path):
    store = StateStore(str(tmp_path / "state.json"))

    store.save({"a": 1})
    store.save({"a": 2})

    assert store.load() == {"a": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")

    assert StateStore(str(path)).load() == {}


def test_non_dict_content_is_ignored(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    assert StateStore(str(path)).load() == {}


def test_an_unwritable_path_degrades_to_memory_and_stops_retrying(tmp_path, caplog):
    """An unwritable volume must not take the monitor loop down or spam the log."""
    blocked = tmp_path / "afile"
    blocked.write_text("not a directory", encoding="utf-8")
    store = StateStore(str(blocked / "state.json"))

    with caplog.at_level("WARNING"):
        store.save({"a": 1})
        store.save({"a": 2})

    assert store.enabled is False
    assert len([r for r in caplog.records if "Could not persist alert state" in r.message]) == 1


def test_path_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECTOR_STATE_PATH", str(tmp_path / "from-env.json"))
    assert StateStore().path == str(tmp_path / "from-env.json")

    monkeypatch.delenv("COLLECTOR_STATE_PATH")
    # Defaults to a mounted volume so state survives container recreation.
    assert StateStore().path == DEFAULT_STATE_PATH


def test_an_explicit_path_beats_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECTOR_STATE_PATH", "/nope/state.json")
    assert StateStore(str(tmp_path / "explicit.json")).path.endswith("explicit.json")
