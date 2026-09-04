import asyncio
import base64
import hashlib
import logging
import os
import ssl
import time

import aiohttp
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from sunsynk.battery import Battery
from sunsynk.grid import Grid
from sunsynk.input import Input
from sunsynk.inverter import Inverter
from sunsynk.output import Output
from sunsynk.plant import Plant

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


class InvalidCredentialsException(Exception):
    def __init__(self):
        super().__init__('Invalid username or password')


class VerificationCodeRequiredException(Exception):
    def __init__(self, message: str = 'Verification code required'):
        super().__init__(message)


class LoginRateLimitedException(Exception):
    def __init__(self, message: str = 'Login rate limited'):
        super().__init__(message)


class SunsynkApiError(Exception):
    def __init__(self, status_code: int, message: str = 'API request failed', response_body: str | None = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"{message} (status={status_code})")


class SunsynkConnectionError(Exception):
    def __init__(self, message: str = 'Connection to Sunsynk API failed'):
        super().__init__(message)


class SunsynkTimeoutError(Exception):
    def __init__(self, message: str = 'Request to Sunsynk API timed out'):
        super().__init__(message)


class SunsynkClient:
    """Async client for the Sunsynk API.

    TLS certificates are verified by default. Verification can only be disabled
    explicitly (``verify_tls=False`` or ``SUNSYNK_VERIFY_TLS=false``) and is
    intended for local development against a proxy, never for deployment.

    The aiohttp session is created on first use rather than in the constructor,
    so a client that is built but never logged in cannot leak a session.
    """

    @classmethod
    async def create(
        cls,
        username: str,
        password: str,
        base_url: str = None,
        debug: bool = False,
        verification_code: str | None = None,
        request_timeout_seconds: float | None = None,
        connect_timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_base_delay_seconds: float | None = None,
        verify_tls: bool | None = None,
    ):
        self = SunsynkClient(
            username,
            password,
            base_url,
            debug=debug,
            verification_code=verification_code,
            request_timeout_seconds=request_timeout_seconds,
            connect_timeout_seconds=connect_timeout_seconds,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            verify_tls=verify_tls,
        )
        return await self.login()

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = None,
        debug: bool = False,
        verification_code: str | None = None,
        request_timeout_seconds: float | None = None,
        connect_timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_base_delay_seconds: float | None = None,
        verify_tls: bool | None = None,
    ):
        self.base_url = 'https://api.sunsynk.net' if base_url is None else base_url
        self.debug = debug
        self.verification_code = verification_code
        self.request_timeout_seconds = (
            float(request_timeout_seconds)
            if request_timeout_seconds is not None
            else float(os.getenv("SUNSYNK_REQUEST_TIMEOUT_SECONDS", "20"))
        )
        self.connect_timeout_seconds = (
            float(connect_timeout_seconds)
            if connect_timeout_seconds is not None
            else float(os.getenv("SUNSYNK_CONNECT_TIMEOUT_SECONDS", "10"))
        )
        self.max_retries = (
            int(max_retries)
            if max_retries is not None
            else int(os.getenv("SUNSYNK_MAX_RETRIES", "3"))
        )
        self.retry_base_delay_seconds = (
            float(retry_base_delay_seconds)
            if retry_base_delay_seconds is not None
            else float(os.getenv("SUNSYNK_RETRY_BASE_DELAY_SECONDS", "0.5"))
        )
        self.verify_tls = (
            bool(verify_tls)
            if verify_tls is not None
            else _env_flag("SUNSYNK_VERIFY_TLS", True)
        )

        # Session is created lazily by __ensure_session so that constructing a
        # client without using it never opens (and leaks) a connection pool.
        self.session = None

        self.access_token = None
        self.refresh_token = None
        self.username = username
        self.password = password
        # None until the first attempt. Not 0.0: time.monotonic() counts from an
        # arbitrary epoch (uptime on Linux), so on a freshly booted host 0.0
        # reads as "a moment ago" and throttles the very first login.
        self._last_login_attempt = None
        self._login_rate_limit_seconds = float(os.getenv("SUNSYNK_LOGIN_RATE_LIMIT_SECONDS", "60"))

    async def __aenter__(self):
        try:
            await self.login()
            return self
        except Exception:
            # Ensure we don't leak open sessions when login fails
            await self.close()
            raise

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        if self.session is not None and not self.session.closed:
            await self.session.close()

    def __connector(self) -> aiohttp.TCPConnector:
        if self.verify_tls:
            return aiohttp.TCPConnector()
        logger.warning(
            "TLS certificate verification is DISABLED for %s. "
            "This is unsafe outside local development.",
            self.base_url,
        )
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return aiohttp.TCPConnector(ssl=ssl_context)

    def __ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(connector=self.__connector())

    async def request_verification_code(self):
        """Request a login verification code for this username.

        The Sunsynk web client calls `GET /anonymous/getVerificationCode?username=...`.
        In practice this may trigger delivery out-of-band (email/SMS), and often returns `data: null`.
        """
        try:
            resp = await self.__request(
                method='GET',
                path='anonymous/getVerificationCode',
                params={'username': self.username},
                headers=self.__headers(),
            )
            body = await resp.json()
        except (SunsynkApiError, SunsynkConnectionError, SunsynkTimeoutError, aiohttp.ClientError):
            return None
        return body

    async def get_plants(self) -> list[Plant]:
        resp = await self.__get('api/v1/plants?page=1&limit=10&name=&status=')
        body = await resp.json()
        plants = body['data']['infos']
        return [Plant(data) for data in plants]

    async def get_inverters(self) -> list[Inverter]:
        resp = await self.__get('api/v1/inverters?page=1&limit=10&total=0&status=-1&sn=&plantId=&type=-2&softVer=&' \
                                'hmiVer=&agentCompanyId=-1&gsn=')
        body = await resp.json()
        inverters = body['data']['infos']
        return [Inverter(data) for data in inverters]

    async def get_inverter_realtime_input(self, inverter_sn: str) -> Input:
        resp = await self.__get(f'api/v1/inverter/{inverter_sn}/realtime/input')
        body = await resp.json()
        return Input(body['data'])

    async def get_inverter_realtime_output(self, inverter_sn: str) -> Output:
        resp = await self.__get(f'api/v1/inverter/{inverter_sn}/realtime/output')
        body = await resp.json()
        return Output(body['data'])

    async def get_inverter_realtime_grid(self, inverter_sn: str) -> Grid:
        resp = await self.__get(f'api/v1/inverter/grid/{inverter_sn}/realtime?sn={inverter_sn}')
        body = await resp.json()
        return Grid(body['data'])

    async def get_inverter_realtime_battery(self, inverter_sn: str) -> Battery:
        resp = await self.__get(f'api/v1/inverter/battery/{inverter_sn}/realtime?sn={inverter_sn}&lan')
        body = await resp.json()
        return Battery(body['data'])

    async def __get(self, path: str, attempts: int = 1):
        resp = await self.__request(method='GET', path=path, headers=self.__headers())
        if resp.status == 401 and attempts == 1:
            # A rejected token is not a login loop: bypass the login throttle so
            # that an expired token within the throttle window stays recoverable.
            await self.login(force=True)
            return await self.__get(path, attempts=attempts + 1)
        if resp.status != 200:
            text = await resp.text()
            raise SunsynkApiError(resp.status, message=f'GET {path} failed', response_body=text)
        return resp

    def __timeout(self) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(total=self.request_timeout_seconds, connect=self.connect_timeout_seconds)

    async def __request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        params: dict | None = None,
        json: dict | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
        retry_on_network_error: bool = True,
    ):
        self.__ensure_session()
        max_retries = self.max_retries if retry_on_network_error else 0
        request_timeout = timeout or self.__timeout()
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self.session.request(
                    method=method,
                    url=self.__url(path),
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=request_timeout,
                )
            except asyncio.TimeoutError as error:
                last_error = error
                if attempt == max_retries:
                    raise SunsynkTimeoutError(
                        f'{method} {path} timed out after {attempt + 1} attempts'
                    ) from error
            except aiohttp.ClientConnectionError as error:
                last_error = error
                if attempt == max_retries:
                    raise SunsynkConnectionError(
                        f'{method} {path} failed after {attempt + 1} attempts due to connection errors'
                    ) from error
            except aiohttp.ClientError as error:
                raise SunsynkConnectionError(
                    f'{method} {path} failed due to HTTP client error'
                ) from error

            delay = self.retry_base_delay_seconds * (2 ** attempt)
            await asyncio.sleep(delay)

        if isinstance(last_error, asyncio.TimeoutError):
            raise SunsynkTimeoutError(f'{method} {path} timed out') from last_error
        if last_error is not None:
            raise SunsynkConnectionError(f'{method} {path} connection failed') from last_error
        raise SunsynkConnectionError(f'{method} {path} request failed')

    def __headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        return headers

    async def login(self, force: bool = False):
        """Authenticate and store an access token.

        Raises LoginRateLimitedException when called more often than
        SUNSYNK_LOGIN_RATE_LIMIT_SECONDS allows, unless ``force`` is set (used
        for token refresh after a 401, which is not a retry of a failed login).
        """
        now = time.monotonic()
        if not force and self._last_login_attempt is not None:
            elapsed = now - self._last_login_attempt
            if elapsed < self._login_rate_limit_seconds:
                remaining = int(self._login_rate_limit_seconds - elapsed)
                raise LoginRateLimitedException(
                    f"Login rate limited. Retry after {remaining}s."
                )
        self._last_login_attempt = now

        # Determine source based on base URL
        source = 'elinter' if 'inteless' in self.base_url else 'sunsynk'

        # Get public key
        nonce = int(time.time() * 1000)
        sign_string = f"nonce={nonce}&source={source}POWER_VIEW"
        sign = hashlib.md5(sign_string.encode()).hexdigest()

        params = {'source': source, 'nonce': nonce, 'sign': sign}

        resp = await self.__request(
            method='GET',
            path='anonymous/publicKey',
            params=params,
            headers=self.__headers(),
        )
        if resp.status != 200:
            body_text = await resp.text()
            raise SunsynkApiError(
                resp.status,
                message='Public key request failed',
                response_body=body_text,
            )

        resp_body = await resp.json()
        if not resp_body['success']:
            raise InvalidCredentialsException()

        public_key_string = resp_body['data']

        # Encrypt password - format public key properly
        pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key_string}\n-----END PUBLIC KEY-----"
        public_key = load_pem_public_key(pem_key.encode('utf-8'))
        encrypted_password = base64.b64encode(
            public_key.encrypt(self.password.encode('utf-8'), PKCS1v15())
        ).decode('utf-8')

        # Login with encrypted password and sign
        token_nonce = int(time.time() * 1000)
        # Matches Sunsynk web client behavior:
        # r = f"nonce={nonce}&source={payload.source}"; sign = md5(r + publicKey[:10])
        token_sign_string = f"nonce={token_nonce}&source={source}{public_key_string[:10]}"
        token_sign = hashlib.md5(token_sign_string.encode()).hexdigest()

        payload = {
            'username': self.username,
            'password': encrypted_password,
            'grant_type': 'password',
            'client_id': 'csp-web',
            'source': source,
            'nonce': token_nonce,
            'sign': token_sign
        }

        # Optional verification/captcha code required after repeated failures (API returns code=114)
        if self.verification_code:
            payload['code'] = self.verification_code

        if self.debug:
            safe_payload = dict(payload)
            safe_payload['password'] = '<redacted>'
            logger.debug("Login URL: %s", self.__url('oauth/token/new'))
            logger.debug("Username: %s", self.username)
            logger.debug("Login request body: %s", safe_payload)
        resp = await self.__request(
            method='POST',
            path='oauth/token/new',
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        if self.debug:
            logger.debug("Login response status: %s", resp.status)
        if resp.status == 200:
            resp_body = await resp.json()
            if resp_body.get('success'):
                self.access_token = resp_body['data']['access_token']
                self.refresh_token = resp_body['data']['refresh_token']
                return self

            # Verification code required
            if resp_body.get('code') == 114:
                if self.verification_code:
                    raise VerificationCodeRequiredException(
                        'Verification code rejected/expired. Request a new one and retry.'
                    )

                # Trigger code delivery and instruct caller to retry with `code`
                await self.request_verification_code()
                raise VerificationCodeRequiredException(
                    'Too many login failures; verification code required. '
                    'Call request_verification_code() and retry with `verification_code` (payload field `code`).'
                )
            raise InvalidCredentialsException()
        text = await resp.text()
        if self.debug:
            logger.debug("Login failed: %s", text[:500])
        raise SunsynkApiError(resp.status, message='Token request failed', response_body=text)

    def __url(self, path: str) -> str:
        return f'{self.base_url}/{path}'
