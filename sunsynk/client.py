import aiohttp
import ssl
import time
import hashlib
import base64
import os
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from sunsynk.battery import Battery
from sunsynk.grid import Grid
from sunsynk.input import Input
from sunsynk.inverter import Inverter
from sunsynk.output import Output
from sunsynk.plant import Plant


class InvalidCredentialsException(Exception):
    def __init__(self):
        super().__init__('Invalid username or password')


class VerificationCodeRequiredException(Exception):
    def __init__(self, message: str = 'Verification code required'):
        super().__init__(message)


class LoginRateLimitedException(Exception):
    def __init__(self, message: str = 'Login rate limited'):
        super().__init__(message)


class SunsynkClient:

    @classmethod
    async def create(
        cls,
        username: str,
        password: str,
        base_url: str = None,
        debug: bool = False,
        verification_code: str | None = None,
    ):
        self = SunsynkClient(username, password, base_url, debug=debug, verification_code=verification_code)
        return await self.login()

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = None,
        debug: bool = False,
        verification_code: str | None = None,
    ):
        self.base_url = 'https://api.sunsynk.net' if base_url is None else base_url
        self.debug = debug
        self.verification_code = verification_code
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        
        self.access_token = None
        self.refresh_token = None
        self.username = username
        self.password = password
        self._last_login_attempt = 0.0
        self._last_login_failure = 0.0
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
        if self.session and not self.session.closed:
            await self.session.close()

    async def request_verification_code(self):
        """Request a login verification code for this username.

        The Sunsynk web client calls `GET /anonymous/getVerificationCode?username=...`.
        In practice this may trigger delivery out-of-band (email/SMS), and often returns `data: null`.
        """
        resp = await self.session.get(
            self.__url('anonymous/getVerificationCode'),
            params={'username': self.username},
            timeout=20,
        )
        if resp.status != 200:
            return None
        try:
            body = await resp.json()
        except Exception:
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
        resp = await self.session.get(self.__url(path), headers=self.__headers(), timeout=20)
        if resp.status == 401 and attempts == 1:
            await self.login()
            return await self.__get(path, attempts=attempts + 1)
        return resp

    async def _notify_login_failure(self, reason: str):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = (
            "Sunsynk login failed\n"
            f"User: {self.username}\n"
            f"Base URL: {self.base_url}\n"
            f"Time: {timestamp}\n"
            f"Reason: {reason}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            await self.session.post(url, json=payload, timeout=10)
        except Exception:
            if self.debug:
                print("Telegram notification failed")

    def __headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        return headers

    async def login(self):
        now = time.monotonic()
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
        
        url = self.__url('anonymous/publicKey')
        params = {'source': source, 'nonce': nonce, 'sign': sign}
        
        resp = await self.session.get(url, params=params, timeout=20)
        if resp.status != 200:
            self._last_login_failure = time.monotonic()
            await self._notify_login_failure(f"publicKey request failed (status {resp.status})")
            raise InvalidCredentialsException()
        
        resp_body = await resp.json()
        if not resp_body['success']:
            self._last_login_failure = time.monotonic()
            await self._notify_login_failure("publicKey response not successful")
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
        
        url = self.__url('oauth/token/new')
        if self.debug:
            safe_payload = dict(payload)
            safe_payload['password'] = '<redacted>'
            print(f"Login URL: {url}")
            print(f"Username: {self.username}")
            print(f"Login request body: {safe_payload}")
        resp = await self.session.post(url,
                                       headers={"Content-Type": "application/json"},
                                       timeout=20,
                                       json=payload)
        if self.debug:
            print(f"Login response status: {resp.status}")
        if resp.status == 200:
            resp_body = await resp.json()
            if self.debug:
                print(f"Login response: {resp_body}")
            if resp_body.get('success'):
                self.access_token = resp_body['data']['access_token']
                self.refresh_token = resp_body['data']['refresh_token']
                return self

            # Verification code required
            if resp_body.get('code') == 114:
                self._last_login_failure = time.monotonic()
                await self._notify_login_failure("verification code required")
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
        else:
            text = await resp.text()
            if self.debug:
                print(f"Login failed: {text[:500]}")
            self._last_login_failure = time.monotonic()
            await self._notify_login_failure(f"token request failed (status {resp.status})")
        raise InvalidCredentialsException()

    def __url(self, path: str) -> str:
        return f'{self.base_url}/{path}'
