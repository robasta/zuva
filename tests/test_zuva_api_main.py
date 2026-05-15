import os
import sys
from dataclasses import dataclass, field
from datetime import datetime

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import zuva_api.main as main_module


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


class FakeRecord:
    def __init__(self, values):
        self.values = values

    def get_time(self):
        return datetime(2026, 1, 1, 12, 0, 0)


class FakeTable:
    def __init__(self, records):
        self.records = records


@pytest.fixture
def client(monkeypatch):
    service = main_module.notification_service
    service.user_settings = {}
    service.telegram_bot = object()

    async def fake_init():
        return None

    async def fake_shutdown():
        return None

    async def fake_save(settings):
        service.user_settings[settings.user_id] = DummySettings(
            user_id=settings.user_id,
            enabled_channels=[c.value for c in settings.enabled_channels],
            telegram_chat_id=settings.telegram_chat_id,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            min_severity=settings.min_severity.value,
            rate_limit_minutes=settings.rate_limit_minutes,
        )

    async def fake_send(alert, user_id):
        return None

    service.initialize = fake_init
    service.shutdown = fake_shutdown
    service.save_user_settings = fake_save
    service.send_alert = fake_send
    service.query_api = type(
        "Q",
        (),
        {
            "query": lambda self, query: [
                FakeTable(
                    [
                        FakeRecord(
                            {
                                "category": "grid_outage",
                                "severity": "high",
                                "title": "Grid",
                                "message": "Down",
                            }
                        )
                    ]
                )
            ]
        },
    )()

    return TestClient(main_module.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["telegram_enabled"] is True


def test_settings_round_trip(client):
    payload = {
        "user_id": "u1",
        "enabled_channels": ["telegram"],
        "telegram_chat_id": "chat",
        "min_severity": "medium",
        "rate_limit_minutes": 20,
    }
    post_resp = client.post("/settings", json=payload)
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "success"

    get_resp = client.get("/settings/u1")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["user_id"] == "u1"
    assert data["enabled_channels"] == ["telegram"]


def test_get_settings_not_found(client):
    r = client.get("/settings/missing")
    assert r.status_code == 404


def test_send_alert_endpoint(client):
    payload = {
        "category": "system_error",
        "severity": "high",
        "title": "Oops",
        "message": "Err",
        "metadata": {"a": 1},
    }
    r = client.post("/alert?user_id=u1", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


def test_get_alert_history_success(client):
    r = client.get("/alerts/history/u1?hours=2")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["category"] == "grid_outage"


def test_get_alert_history_error(client):
    main_module.notification_service.query_api = type(
        "QErr", (), {"query": lambda self, query: (_ for _ in ()).throw(RuntimeError("boom"))}
    )()

    r = client.get("/alerts/history/u1")
    assert r.status_code == 500
