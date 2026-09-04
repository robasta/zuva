"""In-process stand-in for the Sunsynk HTTP API.

Swapped in as a ``SunsynkClient``'s aiohttp session, so the login handshake
(real RSA password encryption, md5 nonce signing) and every resource parser run
against realistic payloads without touching the network.

The public key is a real RSA key generated once per test session: the client
loads it with ``load_pem_public_key`` and encrypts with it, so a broken key
format fails here the same way it would against the live API.
"""
import base64
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ACCESS_TOKEN = "access-token-1"
REFRESH_TOKEN = "refresh-token-1"

_public_key_body = None


def public_key_body() -> str:
    """The base64 DER body the API returns, i.e. a PEM without its headers."""
    global _public_key_body  # pylint: disable=global-statement
    if _public_key_body is None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        der = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        _public_key_body = base64.b64encode(der).decode()
    return _public_key_body


PLANTS_BODY = {
    "success": True,
    "data": {
        "infos": [
            {
                "id": 42,
                "name": "Home",
                "thumbUrl": "https://example.invalid/thumb.png",
                "status": 1,
                "address": "1 Test Road",
                "pac": 1234,
                "efficiency": 0.42,
                "etoday": "5.6",
                "etotal": "1234.5",
                "updateAt": "2026-01-02T03:04:05Z",
                "createAt": "2024-05-06T07:08:09",
                "type": 2,
                "masterId": 7,
                "share": False,
                "plantPermission": ["view"],
                "existCamera": False,
            }
        ]
    },
}

INVERTERS_BODY = {
    "success": True,
    "data": {
        "infos": [
            {
                "sn": "SN-TEST-1",
                "alias": "Inverter 1",
                "gsn": "GSN-1",
                "status": 1,
                "type": 2,
                "commTypeName": "GPRS",
                "custCode": 29,
                "version": {
                    "masterVer": "1.2.3",
                    "softVer": "4.5.6",
                    "hardVer": "7.8.9",
                    "hmiVer": "1.0.0",
                    "bmsVer": "2.0.0",
                },
                "model": "SUN-8K",
                "equipMode": 1,
                "pac": 812,
                "etoday": "5.6",
                "etotal": "1234.5",
                "updateAt": "2026-01-02T03:04:05Z",
                "opened": 1,
                "plant": {
                    "id": 42,
                    "name": "Home",
                    "type": 2,
                    "master": 1,
                    "installer": "Installer",
                    "email": "installer@example.invalid",
                    "phone": "12345",
                },
                "gatewayVO": {"gsn": "GSN-1", "status": 1},
                "sunsynkEquip": True,
                "protocolIdentifier": "2",
            }
        ]
    },
}

BATTERY_BODY = {
    "success": True,
    "data": {
        "etodayChg": "3.1",
        "etodayDischg": "2.2",
        "power": "-450",
        "capacity": "5000",
        "current": "-8.6",
        "voltage": "52.4",
        "temp": "24.5",
        "soc": "64.0",
        "status": 1,
        "numberOfBatteries": 1,
    },
}

GRID_BODY = {
    "success": True,
    "data": {
        "vip": [{"volt": "230.1", "current": "2.5", "power": "575"}],
        "pac": 575,
        "qac": 0,
        "fac": "49.98",
        "pf": "0.99",
        "status": 1,
        "etodayFrom": "1.5",
        "etodayTo": "0.2",
        "etotalFrom": "100.5",
        "etotalTo": "20.2",
    },
}

INPUT_BODY = {
    "success": True,
    "data": {
        "etoday": "5.6",
        "etotal": "1234.5",
        "pac": 1600,
        "pvIV": [
            {
                "id": 1,
                "pvNo": 1,
                "vpv": "320.0",
                "ipv": "2.5",
                "ppv": "800",
                "todayPv": "2.8",
                "sn": "SN-TEST-1",
                "time": "2026-01-02 03:04:05",
            },
            {
                "id": 2,
                "pvNo": 2,
                "vpv": "310.0",
                "ipv": "2.6",
                "ppv": "806",
                "todayPv": "2.8",
                "sn": "SN-TEST-1",
                "time": "2026-01-02 03:04:05",
            },
        ],
    },
}

OUTPUT_BODY = {
    "success": True,
    "data": {
        "vip": [{"volt": "230.5", "current": "3.5", "power": "812"}],
        "pInv": 812,
        "pac": 812,
        "fac": "50.01",
    },
}


class MockResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status = status
        self._body = body if body is not None else {}
        self._text = text

    async def json(self):
        return self._body

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def default_routes():
    """(method, path) -> response body, mirroring the live API's shapes."""
    return {
        ("GET", "/anonymous/publicKey"): {"success": True, "data": public_key_body()},
        ("GET", "/anonymous/getVerificationCode"): {"success": True, "data": None},
        ("POST", "/oauth/token/new"): {
            "success": True,
            "data": {"access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN},
        },
        ("GET", "/api/v1/plants"): PLANTS_BODY,
        ("GET", "/api/v1/inverters"): INVERTERS_BODY,
        ("GET", "/api/v1/inverter/battery/SN-TEST-1/realtime"): BATTERY_BODY,
        ("GET", "/api/v1/inverter/grid/SN-TEST-1/realtime"): GRID_BODY,
        ("GET", "/api/v1/inverter/SN-TEST-1/realtime/input"): INPUT_BODY,
        ("GET", "/api/v1/inverter/SN-TEST-1/realtime/output"): OUTPUT_BODY,
    }


class MockSunsynkApi:
    """Session double: routes by (method, path) and records every request."""

    def __init__(self, routes=None, statuses=None):
        self.routes = default_routes()
        if routes:
            self.routes.update(routes)
        # (method, path) -> HTTP status, for testing non-200 handling.
        self.statuses = statuses or {}
        self.requests = []
        self.closed = False

    def set_body(self, method, path, body):
        self.routes[(method, path)] = body

    def set_status(self, method, path, status):
        self.statuses[(method, path)] = status

    async def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        path = urlparse(url).path
        key = (method, path)
        self.requests.append({
            "method": method,
            "path": path,
            "headers": headers or {},
            "params": params,
            "json": json,
        })

        status = self.statuses.get(key, 200)
        if status != 200:
            return MockResponse(status=status, text=f"error for {method} {path}")
        if key not in self.routes:
            return MockResponse(status=404, text=f"no mock route for {method} {path}")
        return MockResponse(status=200, body=self.routes[key])

    async def close(self):
        self.closed = True

    def paths(self):
        return [request["path"] for request in self.requests]

    def last(self):
        return self.requests[-1]
