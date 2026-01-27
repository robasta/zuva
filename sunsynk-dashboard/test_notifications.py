#!/usr/bin/env python3
"""
Test script for Sunsynk Notification System
Verifies configuration and sends test notifications
"""
import os
import sys
import asyncio
import aiohttp
from datetime import datetime


async def test_notification_api():
    """Test the notification API health"""
    print("🏥 Testing Notification API...")
    
    api_url = os.getenv("NOTIFICATION_API_URL", "http://localhost:8000")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API is healthy")
                    print(f"   - Telegram enabled: {data.get('telegram_enabled')}")
                    print(f"   - Users configured: {data.get('users_configured')}")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to connect to API: {e}")
        print(f"   Make sure the service is running: docker-compose up -d")
        return False


async def test_send_alert(user_id="default"):
    """Send a test alert"""
    print(f"\n📤 Sending test alert to user '{user_id}'...")
    
    api_url = os.getenv("NOTIFICATION_API_URL", "http://localhost:8000")
    
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
                f"{api_url}/alert",
                json=test_alert,
                params={"user_id": user_id}
            ) as response:
                if response.status == 200:
                    print("✅ Test alert sent successfully!")
                    print("   Check your Telegram for the message")
                    return True
                else:
                    text = await response.text()
                    print(f"❌ Failed to send alert: {response.status}")
                    print(f"   Response: {text}")
                    return False
    except Exception as e:
        print(f"❌ Error sending alert: {e}")
        return False


async def check_settings(user_id="default"):
    """Check user settings"""
    print(f"\n⚙️  Checking settings for user '{user_id}'...")
    
    api_url = os.getenv("NOTIFICATION_API_URL", "http://localhost:8000")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/settings/{user_id}") as response:
                if response.status == 200:
                    settings = await response.json()
                    print("✅ User settings found:")
                    print(f"   - Enabled channels: {settings.get('enabled_channels')}")
                    print(f"   - Telegram chat ID: {settings.get('telegram_chat_id') or 'Not set'}")
                    print(f"   - Quiet hours: {settings.get('quiet_hours_start')} - {settings.get('quiet_hours_end')}")
                    print(f"   - Min severity: {settings.get('min_severity')}")
                    return True
                elif response.status == 404:
                    print("⚠️  No settings found for this user")
                    print("   Use the API to configure settings first")
                    return False
                else:
                    print(f"❌ Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error checking settings: {e}")
        return False


async def main():
    """Main test function"""
    print("🔔 Sunsynk Notification System - Test Script")
    print("=" * 50)
    
    # Test API health
    api_ok = await test_notification_api()
    if not api_ok:
        print("\n❌ API is not accessible. Exiting.")
        sys.exit(1)
    
    # Check user settings
    await check_settings()
    
    # Ask user if they want to send test notification
    print("\n" + "=" * 50)
    response = input("\n📤 Send a test notification? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        await test_send_alert()
    else:
        print("Skipping test notification")
    
    print("\n✅ Testing complete!")
    print("\nNext steps:")
    print("  1. Configure your Telegram chat ID")
    print("  2. Set up user settings via POST /settings")
    print("  3. Monitor logs: docker-compose logs -f")
    print("\n🌞 Your notification system is ready!")


if __name__ == "__main__":
    asyncio.run(main())
