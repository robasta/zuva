"""Login handshake and resource parsing against the in-process mock API."""
import base64
import hashlib

import aiohttp
import pytest

from mock_api_server import ACCESS_TOKEN, MockSunsynkApi, REFRESH_TOKEN, public_key_body
from sunsynk.client import (
    InvalidCredentialsException,
    LoginRateLimitedException,
    SunsynkApiError,
    SunsynkClient,
    VerificationCodeRequiredException,
)

BASE_URL = "https://api.test.invalid"


def make_client(api, **kwargs):
    client = SunsynkClient("user@example.invalid", "s3cret", BASE_URL, **kwargs)
    client.session = api
    return client


@pytest.fixture
def api():
    return MockSunsynkApi()


@pytest.mark.asyncio
async def test_login_stores_tokens(api):
    client = make_client(api)

    result = await client.login()

    assert result is client
    assert client.access_token == ACCESS_TOKEN
    assert client.refresh_token == REFRESH_TOKEN
    assert api.paths() == ["/anonymous/publicKey", "/oauth/token/new"]


@pytest.mark.asyncio
async def test_login_signs_the_public_key_request(api):
    client = make_client(api)

    await client.login()

    params = api.requests[0]["params"]
    assert params["source"] == "sunsynk"
    expected = hashlib.md5(
        f"nonce={params['nonce']}&source=sunsynkPOWER_VIEW".encode()
    ).hexdigest()
    assert params["sign"] == expected


@pytest.mark.asyncio
async def test_login_uses_the_elinter_source_for_inteless(api):
    client = SunsynkClient("user", "pass", "https://api.inteless.com")
    client.session = api

    await client.login()

    assert api.requests[0]["params"]["source"] == "elinter"


@pytest.mark.asyncio
async def test_login_encrypts_the_password_and_signs_the_token_request(api):
    client = make_client(api)

    await client.login()

    payload = api.requests[1]["json"]
    assert payload["username"] == "user@example.invalid"
    assert payload["grant_type"] == "password"
    assert payload["client_id"] == "csp-web"
    assert payload["source"] == "sunsynk"
    assert "code" not in payload

    # The plaintext password must never leave the process.
    assert payload["password"] != "s3cret"
    assert len(base64.b64decode(payload["password"])) == 256

    expected_sign = hashlib.md5(
        f"nonce={payload['nonce']}&source=sunsynk{public_key_body()[:10]}".encode()
    ).hexdigest()
    assert payload["sign"] == expected_sign


@pytest.mark.asyncio
async def test_verification_code_is_sent_when_configured(api):
    client = make_client(api, verification_code="123456")

    await client.login()

    assert api.requests[1]["json"]["code"] == "123456"


@pytest.mark.asyncio
async def test_public_key_http_error_raises_api_error(api):
    api.set_status("GET", "/anonymous/publicKey", 503)
    client = make_client(api)

    with pytest.raises(SunsynkApiError) as error:
        await client.login()

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_unsuccessful_public_key_response_raises_invalid_credentials(api):
    api.set_body("GET", "/anonymous/publicKey", {"success": False, "data": None})
    client = make_client(api)

    with pytest.raises(InvalidCredentialsException):
        await client.login()


@pytest.mark.asyncio
async def test_token_http_error_raises_api_error(api):
    api.set_status("POST", "/oauth/token/new", 500)
    client = make_client(api)

    with pytest.raises(SunsynkApiError) as error:
        await client.login()

    assert error.value.status_code == 500


@pytest.mark.asyncio
async def test_unsuccessful_token_response_raises_invalid_credentials(api):
    api.set_body("POST", "/oauth/token/new", {"success": False, "code": 102})
    client = make_client(api)

    with pytest.raises(InvalidCredentialsException):
        await client.login()


@pytest.mark.asyncio
async def test_code_114_requests_a_verification_code(api):
    """Sunsynk demands a code after repeated failures; the client asks for one."""
    api.set_body("POST", "/oauth/token/new", {"success": False, "code": 114})
    client = make_client(api)

    with pytest.raises(VerificationCodeRequiredException, match="verification code required"):
        await client.login()

    assert "/anonymous/getVerificationCode" in api.paths()


@pytest.mark.asyncio
async def test_code_114_with_a_configured_code_reports_it_as_rejected(api):
    api.set_body("POST", "/oauth/token/new", {"success": False, "code": 114})
    client = make_client(api, verification_code="000000")

    with pytest.raises(VerificationCodeRequiredException, match="rejected/expired"):
        await client.login()

    # No point asking for another code when the caller already supplied one.
    assert "/anonymous/getVerificationCode" not in api.paths()


@pytest.mark.asyncio
async def test_request_verification_code_swallows_transport_errors():
    """Best-effort call: a network failure here must not mask the login error."""
    class OfflineSession:
        closed = False

        async def request(self, **kwargs):
            raise aiohttp.ClientConnectionError("offline")

    client = SunsynkClient("user", "pass", BASE_URL, max_retries=0)
    client.session = OfflineSession()

    assert await client.request_verification_code() is None


@pytest.mark.asyncio
async def test_repeated_logins_are_throttled(api):
    client = make_client(api)
    await client.login()

    with pytest.raises(LoginRateLimitedException, match="Retry after"):
        await client.login()

    assert api.paths().count("/oauth/token/new") == 1


@pytest.mark.asyncio
async def test_first_login_is_never_throttled_on_a_freshly_booted_host(api, monkeypatch):
    """time.monotonic() counts from boot, so on a new host it is a small number.

    The throttle must key off "has a login been attempted", not off a sentinel
    timestamp that a low uptime makes look recent.
    """
    monkeypatch.setattr("sunsynk.client.time.monotonic", lambda: 3.0)
    client = make_client(api)

    await client.login()

    assert client.access_token == ACCESS_TOKEN


@pytest.mark.asyncio
async def test_force_bypasses_the_login_throttle(api):
    """Token refresh after a 401 is not a retry of a failed login."""
    client = make_client(api)
    await client.login()

    await client.login(force=True)

    assert api.paths().count("/oauth/token/new") == 2


@pytest.mark.asyncio
async def test_context_manager_closes_the_session_when_login_fails(api):
    api.set_body("POST", "/oauth/token/new", {"success": False, "code": 102})
    client = make_client(api)

    with pytest.raises(InvalidCredentialsException):
        async with client:
            pass

    assert api.closed is True


@pytest.mark.asyncio
async def test_context_manager_closes_the_session_on_exit(api):
    client = make_client(api)

    async with client as entered:
        assert entered is client
        assert api.closed is False

    assert api.closed is True
