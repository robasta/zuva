"""Both copies of timeutil must behave identically.

The module is duplicated because the collector and the API ship as separate
images with no shared package; these tests are what keep the two in step.
"""
from datetime import timezone

import pytest

from zuva.collector import timeutil as collector_timeutil
from zuva_api import timeutil as api_timeutil

MODULES = [collector_timeutil, api_timeutil]


@pytest.fixture(autouse=True)
def clear_cache():
    for module in MODULES:
        module._cache.clear()
    yield
    for module in MODULES:
        module._cache.clear()


@pytest.mark.parametrize("module", MODULES)
def test_defaults_to_the_site_timezone(module, monkeypatch):
    monkeypatch.delenv("TIMEZONE", raising=False)

    assert str(module.get_timezone()) == module.DEFAULT_TIMEZONE
    assert module.DEFAULT_TIMEZONE == "Africa/Johannesburg"


@pytest.mark.parametrize("module", MODULES)
def test_reads_the_timezone_from_the_environment(module, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "Europe/London")

    assert str(module.get_timezone()) == "Europe/London"


@pytest.mark.parametrize("module", MODULES)
def test_unknown_timezone_falls_back_to_utc(module, monkeypatch, caplog):
    monkeypatch.setenv("TIMEZONE", "Mars/Olympus_Mons")

    with caplog.at_level("ERROR"):
        assert str(module.get_timezone()) == "UTC"

    assert "Unknown TIMEZONE" in caplog.text


@pytest.mark.parametrize("module", MODULES)
def test_local_now_is_timezone_aware(module, monkeypatch):
    monkeypatch.setenv("TIMEZONE", "Africa/Johannesburg")
    now = module.local_now()

    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 2 * 3600


@pytest.mark.parametrize("module", MODULES)
def test_local_now_differs_from_naive_utc(module, monkeypatch):
    """The whole point: quiet hours must not be evaluated against the container clock."""
    monkeypatch.setenv("TIMEZONE", "Africa/Johannesburg")
    local = module.local_now()
    utc = local.astimezone(timezone.utc)

    assert local.hour == (utc.hour + 2) % 24


def test_the_two_copies_agree(monkeypatch):
    monkeypatch.setenv("TIMEZONE", "Europe/London")

    assert str(collector_timeutil.get_timezone()) == str(api_timeutil.get_timezone())
    assert collector_timeutil.DEFAULT_TIMEZONE == api_timeutil.DEFAULT_TIMEZONE
