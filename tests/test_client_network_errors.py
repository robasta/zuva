import asyncio
from unittest.mock import AsyncMock

import aiohttp
import pytest

from sunsynk.client import (
    SunsynkApiError,
    SunsynkClient,
    SunsynkConnectionError,
    SunsynkTimeoutError,
)


class FakeResponse:
    def __init__(self, status: int, body: dict | None = None, text: str = ""):
        self.status = status
        self._body = body or {}
        self._text = text

    async def json(self):
        return self._body

    async def text(self):
        return self._text


class FakeSession:
    def __init__(self, events):
        self.events = list(events)
        self.closed = False

    async def request(self, **kwargs):
        event = self.events.pop(0)
        if isinstance(event, Exception):
            raise event
        return event

    async def close(self):
        self.closed = True


async def _build_client(fake_session: FakeSession, **kwargs) -> SunsynkClient:
    client = SunsynkClient("user", "pass", **kwargs)
    # The real client creates its session lazily on first request; pre-seeding it
    # here means no socket is ever opened.
    client.session = fake_session
    return client


@pytest.mark.asyncio
async def test_get_retries_connection_errors_then_raises(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("sunsynk.client.asyncio.sleep", sleep_mock)

    fake_session = FakeSession([
        aiohttp.ClientConnectionError("offline"),
        aiohttp.ClientConnectionError("offline"),
        aiohttp.ClientConnectionError("offline"),
        aiohttp.ClientConnectionError("offline"),
    ])
    client = await _build_client(
        fake_session,
        max_retries=3,
        retry_base_delay_seconds=0.25,
    )

    with pytest.raises(SunsynkConnectionError):
        await client._SunsynkClient__get("api/v1/plants?page=1")

    assert sleep_mock.await_count == 3
    assert [call.args[0] for call in sleep_mock.await_args_list] == [0.25, 0.5, 1.0]


@pytest.mark.asyncio
async def test_get_retries_timeouts_then_raises(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("sunsynk.client.asyncio.sleep", sleep_mock)

    fake_session = FakeSession([
        asyncio.TimeoutError(),
        asyncio.TimeoutError(),
        asyncio.TimeoutError(),
        asyncio.TimeoutError(),
    ])
    client = await _build_client(
        fake_session,
        max_retries=3,
        retry_base_delay_seconds=0.1,
    )

    with pytest.raises(SunsynkTimeoutError):
        await client._SunsynkClient__get("api/v1/plants?page=1")

    assert sleep_mock.await_count == 3


@pytest.mark.asyncio
async def test_get_non_200_raises_api_error():
    fake_session = FakeSession([FakeResponse(status=503, text="service unavailable")])
    client = await _build_client(fake_session, max_retries=0)

    with pytest.raises(SunsynkApiError) as error:
        await client._SunsynkClient__get("api/v1/plants?page=1")

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_get_401_refreshes_token_once():
    fake_session = FakeSession([
        FakeResponse(status=401, body={"success": False}),
        FakeResponse(status=200, body={"success": True}),
    ])
    client = await _build_client(fake_session, max_retries=0)
    client.login = AsyncMock(return_value=client)

    response = await client._SunsynkClient__get("api/v1/plants?page=1")

    assert response.status == 200
    client.login.assert_awaited_once()
    # A rejected token must bypass the login throttle, otherwise the retry is
    # guaranteed to raise LoginRateLimitedException instead of recovering.
    assert client.login.await_args.kwargs == {"force": True}


def test_verify_tls_defaults_on(monkeypatch):
    monkeypatch.delenv("SUNSYNK_VERIFY_TLS", raising=False)
    assert SunsynkClient("user", "pass").verify_tls is True


def test_verify_tls_can_be_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SUNSYNK_VERIFY_TLS", "false")
    assert SunsynkClient("user", "pass").verify_tls is False


def test_verify_tls_argument_beats_env(monkeypatch):
    monkeypatch.setenv("SUNSYNK_VERIFY_TLS", "false")
    assert SunsynkClient("user", "pass", verify_tls=True).verify_tls is True


def test_session_is_not_created_in_constructor():
    assert SunsynkClient("user", "pass").session is None


@pytest.mark.asyncio
async def test_close_is_safe_without_a_session():
    await SunsynkClient("user", "pass").close()
