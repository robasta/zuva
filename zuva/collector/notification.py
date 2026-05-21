import aiohttp
import logging
import os
from urllib.parse import urlparse, urlunparse

class NotificationSender:
    def __init__(self, api_url, user_id):
        self.api_urls = self._build_candidate_urls(api_url)
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)

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

    async def send(self, category, severity, title, message, metadata=None):
        payload = {
            "category": category,
            "severity": severity,
            "title": title,
            "message": message,
            "metadata": metadata or {}
        }

        for index, api_url in enumerate(self.api_urls):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{api_url}/alert",
                        json=payload,
                        params={"user_id": self.user_id}
                    ) as response:
                        if response.status == 200:
                            self.logger.info(f"Alert sent: {category}")
                            return
                        self.logger.error(
                            f"Failed to send alert via {api_url}: {response.status}"
                        )
            except Exception as error:
                self.logger.error(f"Error sending alert via {api_url}: {error}")

            if index < len(self.api_urls) - 1:
                self.logger.warning(
                    f"Retrying alert delivery with fallback URL: {self.api_urls[index + 1]}"
                )
