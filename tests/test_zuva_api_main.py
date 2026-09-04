from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

import zuva_api.main as main_module
from zuva_api.history_store import HistoryStore

API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}


@dataclass
class DummySettings:
    user_id: str
    enabled_channels: list[str]
    telegram_chat_id: str | None = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    min_severity: str = "medium"
    rate_limit_minutes: int = 15
    last_alert_times: dict = field(default_factory=dict)


@pytest.fixture
def history(tmp_path):
    """A real SQLite history on a temp path, so the endpoints exercise real SQL."""
    store = HistoryStore(str(tmp_path / "zuva.db"))
    store.initialize()
    return store


@pytest.fixture
def service(monkeypatch, history):
    monkeypatch.setattr(main_module, "ZUVA_API_KEY", API_KEY)
    svc = main_module.notification_service
    monkeypatch.setattr(svc, "user_settings", {})
    monkeypatch.setattr(svc, "telegram_bot", object())
    monkeypatch.setattr(svc, "history_store", history)

    async def fake_init():
        return None

    async def fake_save(settings):
        svc.user_settings[settings.user_id] = DummySettings(
            user_id=settings.user_id,
            enabled_channels=[c.value for c in settings.enabled_channels],
            telegram_chat_id=settings.telegram_chat_id,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            min_severity=settings.min_severity.value,
            rate_limit_minutes=settings.rate_limit_minutes,
        )

    async def fake_send(alert, user_id):
        return {"status": "sent"}

    monkeypatch.setattr(svc, "initialize", fake_init)
    monkeypatch.setattr(svc, "save_user_settings", fake_save)
    monkeypatch.setattr(svc, "send_alert", fake_send)
    return svc


@pytest.fixture
def client(service):
    with TestClient(main_module.app) as test_client:
        yield test_client


SETTINGS_PAYLOAD = {
    "user_id": "u1",
    "enabled_channels": ["telegram"],
    "telegram_chat_id": "chat",
    "min_severity": "medium",
    "rate_limit_minutes": 20,
}

ALERT_PAYLOAD = {
    "category": "system_error",
    "severity": "high",
    "title": "Oops",
    "message": "Err",
    "metadata": {"a": 1},
}

TELEMETRY_PAYLOAD = {
    "inverter_sn": "SN1",
    "plant_id": "7",
    "load_power_w": 812.0,
    "grid_power_w": -45.0,
    "battery_soc": 64.0,
    "grid_voltage": 230.1,
    "grid_status": 1,
}


def test_startup_refuses_to_run_without_an_api_key(monkeypatch, service):
    monkeypatch.setattr(main_module, "ZUVA_API_KEY", None)

    with pytest.raises(RuntimeError, match="ZUVA_API_KEY"):
        with TestClient(main_module.app):
            pass


def test_health_needs_no_api_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["telegram_enabled"] is True


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/settings", SETTINGS_PAYLOAD),
        ("get", "/settings/u1", None),
        ("post", "/alert?user_id=u1", ALERT_PAYLOAD),
        ("post", "/telemetry", TELEMETRY_PAYLOAD),
        ("get", "/alerts/history/u1", None),
    ],
)
def test_endpoints_require_an_api_key(client, method, path, payload):
    unauthenticated = client.request(method.upper(), path, json=payload)
    assert unauthenticated.status_code == 401

    wrong_key = client.request(
        method.upper(), path, json=payload, headers={"X-API-Key": "wrong"}
    )
    assert wrong_key.status_code == 401


def test_settings_round_trip(client):
    post_resp = client.post("/settings", json=SETTINGS_PAYLOAD, headers=AUTH)
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "success"

    get_resp = client.get("/settings/u1", headers=AUTH)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["user_id"] == "u1"
    assert data["enabled_channels"] == ["telegram"]


def test_get_settings_not_found(client):
    r = client.get("/settings/missing", headers=AUTH)
    assert r.status_code == 404


def test_rejects_user_ids_outside_the_allowed_pattern(client):
    r = client.get("/settings/../etc", headers=AUTH)
    assert r.status_code in (404, 422)

    r = client.get("/alerts/history/bad%20id", headers=AUTH)
    assert r.status_code == 422


def test_send_alert_endpoint(client):
    r = client.post("/alert?user_id=u1", json=ALERT_PAYLOAD, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


def test_send_alert_reports_suppression(client, service, monkeypatch):
    async def suppressed(alert, user_id):
        return {"status": "suppressed", "reason": "quiet_hours"}

    monkeypatch.setattr(service, "send_alert", suppressed)

    r = client.post("/alert?user_id=u1", json=ALERT_PAYLOAD, headers=AUTH)

    assert r.status_code == 200
    assert r.json() == {"status": "suppressed", "reason": "quiet_hours"}


def test_send_alert_unknown_user_is_a_conflict(client, service, monkeypatch):
    """An alert with nowhere to go must not look like a successful delivery."""
    async def unknown(alert, user_id):
        return {"status": "unknown_user", "reason": "no settings configured for user ghost"}

    monkeypatch.setattr(service, "send_alert", unknown)

    r = client.post("/alert?user_id=ghost", json=ALERT_PAYLOAD, headers=AUTH)

    assert r.status_code == 409
    assert "ghost" in r.json()["detail"]


def test_send_alert_delivery_failure_is_a_bad_gateway(client, service, monkeypatch):
    async def failed(alert, user_id):
        return {"status": "failed", "reason": "all_channels_failed"}

    monkeypatch.setattr(service, "send_alert", failed)

    r = client.post("/alert?user_id=u1", json=ALERT_PAYLOAD, headers=AUTH)

    assert r.status_code == 502


def test_collector_login_failure_category_is_accepted(client):
    """The collector's "monitoring is broken" alert used to be rejected as 422."""
    payload = dict(ALERT_PAYLOAD, category="sunsynk_login_failure", severity="critical")

    r = client.post("/alert?user_id=u1", json=payload, headers=AUTH)

    assert r.status_code == 200


def test_get_alert_history_success(client, history):
    history.record_alert("u1", "grid_outage", "high", "Grid", "Down")

    r = client.get("/alerts/history/u1?hours=2", headers=AUTH)

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["category"] == "grid_outage"
    assert data[0]["title"] == "Grid"


def test_alert_history_is_scoped_to_the_path_user(client, history):
    """The user id is a bound parameter, so it can only ever match one user."""
    history.record_alert("u1", "grid_outage", "high", "Mine", "m")
    history.record_alert("u2", "grid_outage", "high", "Theirs", "t")

    r = client.get("/alerts/history/u1?hours=3", headers=AUTH)

    assert [row["title"] for row in r.json()] == ["Mine"]


def test_alert_history_rejects_out_of_range_hours(client):
    assert client.get("/alerts/history/u1?hours=0", headers=AUTH).status_code == 422
    assert client.get("/alerts/history/u1?hours=100000", headers=AUTH).status_code == 422


def test_get_alert_history_error_does_not_leak_internals(client, history, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(history, "recent_alerts", boom)

    r = client.get("/alerts/history/u1", headers=AUTH)

    assert r.status_code == 500
    assert r.json()["detail"] == "Could not read alert history"


def test_telemetry_is_stored(client, history):
    r = client.post("/telemetry", json=TELEMETRY_PAYLOAD, headers=AUTH)

    assert r.status_code == 200
    assert r.json() == {"status": "stored"}

    with history._connect() as conn:
        row = conn.execute("SELECT * FROM readings").fetchone()
    assert row["inverter_sn"] == "SN1"
    assert row["load_power_w"] == 812.0
    assert row["grid_status"] == 1


def test_telemetry_accepts_a_reading_without_the_optional_fields(client, history):
    payload = {
        "inverter_sn": "SN2",
        "load_power_w": 1.0,
        "grid_power_w": 2.0,
        "battery_soc": 3.0,
    }

    r = client.post("/telemetry", json=payload, headers=AUTH)

    assert r.status_code == 200
    with history._connect() as conn:
        row = conn.execute("SELECT * FROM readings").fetchone()
    assert row["grid_voltage"] is None


def test_telemetry_rejects_a_malformed_reading(client):
    r = client.post("/telemetry", json={"plant_id": "7"}, headers=AUTH)
    assert r.status_code == 422


def test_telemetry_write_failure_does_not_leak_internals(client, history, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(history, "record_reading", boom)

    r = client.post("/telemetry", json=TELEMETRY_PAYLOAD, headers=AUTH)

    assert r.status_code == 500
    assert r.json()["detail"] == "Could not store telemetry"
