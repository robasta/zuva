import logging
import os
from urllib.parse import urlparse, urlunparse

import aiohttp


class NotificationSender:
    """The collector's HTTP client for zuva-api: alerts and telemetry.

    Holds one aiohttp session for the process lifetime rather than building a
    connection pool per request. Nothing here raises: a notification API that is
    down must not take the poll loop with it.
    """

    def __init__(self, api_url, user_id, api_key=None, timeout_seconds=None):
        self.api_urls = self._build_candidate_urls(api_url)
        self.user_id = user_id
        self.api_key = api_key if api_key is not None else os.getenv("ZUVA_API_KEY")
        self.timeout_seconds = float(
            timeout_seconds if timeout_seconds is not None
            else os.getenv("NOTIFICATION_TIMEOUT_SECONDS", "15")
        )
        self.logger = logging.getLogger(__name__)
        self._session = None
        if not self.api_key:
            self.logger.warning(
                "ZUVA_API_KEY is not set; the notification API will reject these alerts"
            )

    @staticmethod
    def _build_candidate_urls(api_url):
        candidates = [api_url.rstrip("/")]
        parsed = urlparse(api_url)
        running_in_container = os.path.exists("/.dockerenv")

        # Only use localhost fallback when running outside Docker.
        if parsed.hostname == "zuva-api" and not running_in_container:
            localhost_netloc = "localhost"
            if parsed.port is not None:
                localhost_netloc = f"localhost:{parsed.port}"
            localhost_url = urlunparse(
                (
                    parsed.scheme or "http",
                    localhost_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            ).rstrip("/")
            if localhost_url not in candidates:
                candidates.append(localhost_url)

        return candidates

    def _ensure_session(self):
        if self._session is None or getattr(self._session, "closed", False):
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
            )
        return self._session

    def _headers(self):
        return {"X-API-Key": self.api_key} if self.api_key else {}

    async def aclose(self):
        if self._session is not None and not getattr(self._session, "closed", False):
            await self._session.close()
        self._session = None

    async def send(self, category, severity, title, message, metadata=None):
        payload = {
            "category": category,
            "severity": severity,
            "title": title,
            "message": message,
            "metadata": metadata or {}
        }
        await self._post(
            "/alert",
            payload,
            params={"user_id": self.user_id},
            description=f"alert {category}",
        )

    async def send_telemetry(self, reading):
        """POST one poll's readings. zuva-api owns the database, not the collector."""
        await self._post("/telemetry", reading, params=None, description="telemetry")

    async def _post(self, path, payload, params, description):
        session = self._ensure_session()
        for index, api_url in enumerate(self.api_urls):
            try:
                async with session.post(
                    f"{api_url}{path}",
                    json=payload,
                    params=params,
                    headers=self._headers(),
                ) as response:
                    if response.status == 200:
                        self.logger.info("Sent %s", description)
                        return
                    body = await self._safe_body(response)
                    self.logger.error(
                        "Failed to send %s via %s: %s %s",
                        description, api_url, response.status, body,
                    )
            except Exception as error:  # pylint: disable=broad-except
                self.logger.error("Error sending %s via %s: %s", description, api_url, error)

            if index < len(self.api_urls) - 1:
                self.logger.warning(
                    "Retrying %s with fallback URL: %s", description, self.api_urls[index + 1]
                )

    @staticmethod
    async def _safe_body(response):
        try:
            return (await response.text())[:200]
        except Exception:  # pylint: disable=broad-except
            return ""
