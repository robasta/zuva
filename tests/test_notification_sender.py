import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zuva.collector.notification import NotificationSender


class FakeResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, status=200, capture=None):
        self.status = status
        self.capture = capture if capture is not None else {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json, params):
        self.capture["url"] = url
        self.capture["json"] = json
        self.capture["params"] = params
        return FakeResponse(self.status)


class MultiAttemptSession:
    def __init__(self, behavior, capture):
        self.behavior = behavior
        self.capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json, params):
        self.capture.setdefault("urls", []).append(url)
        self.capture["json"] = json
        self.capture["params"] = params

        action = self.behavior.get(url, "ok")
        if isinstance(action, Exception):
            raise action
        if action == "ok":
            return FakeResponse(200)
        return FakeResponse(action)


@pytest.mark.asyncio
async def test_send_success_logs_info(monkeypatch):
    capture = {}

    def fake_client_session():
        return FakeSession(status=200, capture=capture)

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", fake_client_session)

    sender = NotificationSender("http://api", "u1")
    await sender.send("grid_outage", "high", "Title", "Message", {"x": 1})

    assert capture["url"] == "http://api/alert"
    assert capture["params"] == {"user_id": "u1"}
    assert capture["json"]["metadata"] == {"x": 1}


@pytest.mark.asyncio
async def test_send_uses_empty_metadata_when_none(monkeypatch):
    capture = {}

    def fake_client_session():
        return FakeSession(status=200, capture=capture)

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", fake_client_session)

    sender = NotificationSender("http://api", "u2")
    await sender.send("battery_low", "high", "Title", "Message", None)

    assert capture["json"]["metadata"] == {}


@pytest.mark.asyncio
async def test_send_non_200_does_not_raise(monkeypatch):
    def fake_client_session():
        return FakeSession(status=500, capture={})

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", fake_client_session)

    sender = NotificationSender("http://api", "u3")
    await sender.send("battery_critical", "critical", "Title", "Message", {})


@pytest.mark.asyncio
async def test_send_handles_session_exception(monkeypatch):
    class ExplodingSession:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", lambda: ExplodingSession())

    sender = NotificationSender("http://api", "u4")
    await sender.send("system_error", "high", "Title", "Message", {})


def test_builds_localhost_fallback_for_docker_service_name():
    sender = NotificationSender("http://zuva-api:8001", "u5")

    assert sender.api_urls == ["http://zuva-api:8001", "http://localhost:8001"]


@pytest.mark.asyncio
async def test_send_retries_with_localhost_fallback(monkeypatch):
    capture = {}

    def fake_client_session():
        return MultiAttemptSession(
            behavior={
                "http://zuva-api:8001/alert": RuntimeError("dns failure"),
                "http://localhost:8001/alert": "ok",
            },
            capture=capture,
        )

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", fake_client_session)

    sender = NotificationSender("http://zuva-api:8001", "u6")
    await sender.send("grid_outage", "high", "Title", "Message", {"x": 2})

    assert capture["urls"] == ["http://zuva-api:8001/alert", "http://localhost:8001/alert"]
    assert capture["params"] == {"user_id": "u6"}
    assert capture["json"]["metadata"] == {"x": 2}
