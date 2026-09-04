import pytest

from zuva.collector.notification import NotificationSender


class FakeResponse:
    def __init__(self, status, text="body"):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    """Stands in for the single long-lived aiohttp session."""

    def __init__(self, behavior=None, status=200, capture=None):
        self.behavior = behavior or {}
        self.status = status
        self.capture = capture if capture is not None else {}
        self.closed = False

    def post(self, url, json, params, headers):
        self.capture["url"] = url
        self.capture.setdefault("urls", []).append(url)
        self.capture["json"] = json
        self.capture["params"] = params
        self.capture["headers"] = headers

        action = self.behavior.get(url, self.status)
        if isinstance(action, Exception):
            raise action
        return FakeResponse(action)

    async def close(self):
        self.closed = True


def install_session(monkeypatch, session):
    """Patch the session factory and return the number of times it was called."""
    calls = []

    def factory(**kwargs):
        calls.append(kwargs)
        return session

    monkeypatch.setattr("zuva.collector.notification.aiohttp.ClientSession", factory)
    return calls


@pytest.mark.asyncio
async def test_send_success_posts_payload(monkeypatch):
    session = FakeSession()
    install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u1", api_key="secret")
    await sender.send("grid_outage", "high", "Title", "Message", {"x": 1})

    assert session.capture["url"] == "http://api/alert"
    assert session.capture["params"] == {"user_id": "u1"}
    assert session.capture["json"]["metadata"] == {"x": 1}
    assert session.capture["headers"] == {"X-API-Key": "secret"}


@pytest.mark.asyncio
async def test_send_uses_empty_metadata_when_none(monkeypatch):
    session = FakeSession()
    install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u2", api_key="secret")
    await sender.send("battery_low", "high", "Title", "Message", None)

    assert session.capture["json"]["metadata"] == {}


@pytest.mark.asyncio
async def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("ZUVA_API_KEY", "from-env")
    session = FakeSession()
    install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u2b")
    await sender.send("battery_low", "high", "Title", "Message", None)

    assert session.capture["headers"] == {"X-API-Key": "from-env"}


@pytest.mark.asyncio
async def test_no_api_key_sends_no_header(monkeypatch):
    monkeypatch.delenv("ZUVA_API_KEY", raising=False)
    session = FakeSession()
    install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u2c")
    await sender.send("battery_low", "high", "Title", "Message", None)

    assert session.capture["headers"] == {}


@pytest.mark.asyncio
async def test_send_non_200_does_not_raise(monkeypatch):
    install_session(monkeypatch, FakeSession(status=500))

    sender = NotificationSender("http://api", "u3", api_key="secret")
    await sender.send("battery_critical", "critical", "Title", "Message", {})


@pytest.mark.asyncio
async def test_send_handles_session_exception(monkeypatch):
    install_session(monkeypatch, FakeSession(status=RuntimeError("boom")))

    sender = NotificationSender("http://api", "u4", api_key="secret")
    await sender.send("system_error", "high", "Title", "Message", {})


@pytest.mark.asyncio
async def test_session_is_reused_across_alerts(monkeypatch):
    session = FakeSession()
    calls = install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u7", api_key="secret")
    await sender.send("grid_outage", "high", "Title", "Message", {})
    await sender.send("grid_restored", "medium", "Title", "Message", {})

    assert len(calls) == 1
    assert calls[0]["timeout"].total == sender.timeout_seconds


@pytest.mark.asyncio
async def test_aclose_closes_the_session(monkeypatch):
    session = FakeSession()
    install_session(monkeypatch, session)

    sender = NotificationSender("http://api", "u8", api_key="secret")
    await sender.send("grid_outage", "high", "Title", "Message", {})
    await sender.aclose()

    assert session.closed is True
    assert sender._session is None


@pytest.mark.asyncio
async def test_aclose_is_safe_before_any_alert():
    await NotificationSender("http://api", "u9", api_key="secret").aclose()


def test_builds_localhost_fallback_for_docker_service_name():
    sender = NotificationSender("http://zuva-api:8001", "u5", api_key="secret")

    assert sender.api_urls == ["http://zuva-api:8001", "http://localhost:8001"]


@pytest.mark.asyncio
async def test_send_retries_with_localhost_fallback(monkeypatch):
    session = FakeSession(
        behavior={
            "http://zuva-api:8001/alert": RuntimeError("dns failure"),
            "http://localhost:8001/alert": 200,
        }
    )
    install_session(monkeypatch, session)

    sender = NotificationSender("http://zuva-api:8001", "u6", api_key="secret")
    await sender.send("grid_outage", "high", "Title", "Message", {"x": 2})

    assert session.capture["urls"] == [
        "http://zuva-api:8001/alert",
        "http://localhost:8001/alert",
    ]
    assert session.capture["params"] == {"user_id": "u6"}
    assert session.capture["json"]["metadata"] == {"x": 2}
