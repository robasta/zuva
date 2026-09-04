"""The heartbeat is what lets the container healthcheck notice a wedged loop."""
import os
import time

import pytest

from zuva.collector import heartbeat


@pytest.fixture(autouse=True)
def heartbeat_file(tmp_path, monkeypatch):
    path = tmp_path / "heartbeat"
    monkeypatch.setenv("HEARTBEAT_PATH", str(path))
    return path


def test_age_is_none_before_the_first_poll():
    assert heartbeat.age_seconds() is None


def test_touch_records_a_fresh_timestamp(heartbeat_file):
    heartbeat.touch()

    assert heartbeat_file.exists()
    assert heartbeat.age_seconds() < 5


def test_touch_survives_an_unwritable_path(monkeypatch, tmp_path):
    monkeypatch.setenv("HEARTBEAT_PATH", str(tmp_path / "nope" / "heartbeat"))

    heartbeat.touch()  # must not raise: a healthcheck detail cannot break polling

    assert heartbeat.age_seconds() is None


def test_max_age_scales_with_the_poll_interval(monkeypatch):
    monkeypatch.setenv("POLL_INTERVAL", "600")
    assert heartbeat.max_age_seconds() == 1860

    # Floor for fast polling, so a 5s interval does not produce a 75s budget.
    monkeypatch.setenv("POLL_INTERVAL", "5")
    assert heartbeat.max_age_seconds() == 180


def test_main_fails_when_no_heartbeat_exists(capsys):
    assert heartbeat.main() == 1
    assert "no heartbeat" in capsys.readouterr().out


def test_main_succeeds_for_a_fresh_heartbeat(capsys):
    heartbeat.touch()

    assert heartbeat.main() == 0
    assert "ok" in capsys.readouterr().out


def test_main_fails_for_a_stale_heartbeat(heartbeat_file, capsys):
    heartbeat.touch()
    stale = time.time() - (heartbeat.max_age_seconds() + 60)
    os.utime(heartbeat_file, (stale, stale))

    assert heartbeat.main() == 1
    assert "stale" in capsys.readouterr().out
