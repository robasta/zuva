import aiohttp
import logging

class NotificationSender:
    def __init__(self, api_url, user_id):
        self.api_url = api_url
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)

    async def send(self, category, severity, title, message, metadata=None):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "metadata": metadata or {}
                }
                async with session.post(
                    f"{self.api_url}/alert",
                    json=payload,
                    params={"user_id": self.user_id}
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert sent: {category}")
                    else:
                        self.logger.error(f"Failed to send alert: {response.status}")
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
