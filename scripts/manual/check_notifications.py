#!/usr/bin/env python3
"""Manual smoke check for the notification API.

Talks to a running service, so it is not part of the pytest suite. Needs
``ZUVA_API_KEY`` (the same value the service and collector use) and optionally
``NOTIFICATION_API_URL`` and ``DEFAULT_USER_ID``.

    ZUVA_API_KEY=... ./venv/bin/python scripts/manual/check_notifications.py
"""
import os
import sys
import asyncio
import aiohttp
from datetime import datetime

API_URL = os.getenv("NOTIFICATION_API_URL", "http://localhost:8001")
API_KEY = os.getenv("ZUVA_API_KEY")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "robasta")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}


async def check_api_health():
    """/health is the only endpoint that needs no API key."""
    print("🏥 Testing Notification API...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ API is healthy")
                    print(f"   - Telegram enabled: {data.get('telegram_enabled')}")
                    print(f"   - Users configured: {data.get('users_configured')}")
                    return True
                print(f"❌ API returned status {response.status}")
                return False
    except Exception as e:
        print(f"❌ Failed to connect to API: {e}")
        print(
            "   Make sure the service is running: "
            "docker compose --env-file .env -f docker-compose.yml up -d"
        )
        return False


async def send_test_alert(user_id=DEFAULT_USER_ID):
    """Send a test alert"""
    print(f"\n📤 Sending test alert to user '{user_id}'...")

    test_alert = {
        "category": "system_error",
        "severity": "medium",
        "title": "Test Notification",
        "message": f"This is a test notification sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "metadata": {
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/alert",
                json=test_alert,
                params={"user_id": user_id},
                headers=HEADERS,
            ) as response:
                if response.status == 200:
                    print(f"✅ Test alert accepted: {await response.json()}")
                    print("   Check your Telegram for the message")
                    return True
                text = await response.text()
                print(f"❌ Failed to send alert: {response.status}")
                print(f"   Response: {text}")
                return False
    except Exception as e:
        print(f"❌ Error sending alert: {e}")
        return False


async def check_settings(user_id=DEFAULT_USER_ID):
    """Check user settings"""
    print(f"\n⚙️  Checking settings for user '{user_id}'...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/settings/{user_id}", headers=HEADERS) as response:
                if response.status == 200:
                    settings = await response.json()
                    print("✅ User settings found:")
                    print(f"   - Enabled channels: {settings.get('enabled_channels')}")
                    print(f"   - Telegram chat ID: {settings.get('telegram_chat_id') or 'Not set'}")
                    print(f"   - Quiet hours: {settings.get('quiet_hours_start')} - {settings.get('quiet_hours_end')}")
                    print(f"   - Min severity: {settings.get('min_severity')}")
                    return True
                if response.status == 401:
                    print("❌ Rejected: set ZUVA_API_KEY to the value the service was started with")
                    return False
                if response.status == 404:
                    print("⚠️  No settings found for this user")
                    print("   Use the API to configure settings first")
                    return False
                print(f"❌ Error: {response.status}")
                return False
    except Exception as e:
        print(f"❌ Error checking settings: {e}")
        return False


async def main():
    print("🔔 Sunsynk Notification System - Test Script")
    print("=" * 50)

    if not API_KEY:
        print("⚠️  ZUVA_API_KEY is not set; every endpoint except /health will return 401")

    if not await check_api_health():
        print("\n❌ API is not accessible. Exiting.")
        sys.exit(1)

    await check_settings()

    print("\n" + "=" * 50)
    response = input("\n📤 Send a test notification? (y/n): ")

    if response.lower() in ['y', 'yes']:
        await send_test_alert()
    else:
        print("Skipping test notification")

    print("\n✅ Testing complete!")
    print("\nNext steps:")
    print("  1. Configure your Telegram chat ID")
    print("  2. Set up user settings via POST /settings")
    print("  3. Monitor logs: docker compose --env-file .env -f docker-compose.yml logs -f")


if __name__ == "__main__":
    asyncio.run(main())
