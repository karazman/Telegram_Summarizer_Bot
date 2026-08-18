#!/usr/bin/env python3
"""
Setup Telegram webhook for deployed Azure Functions.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv("local.settings.json")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FUNCTION_APP_NAME = input("Enter Azure Function App name: ")
WEBHOOK_URL = f"https://{FUNCTION_APP_NAME}.azurewebsites.net/api/telegram"

print()
print("=" * 60)
print("Telegram Webhook Setup")
print("=" * 60)
print()

if not BOT_TOKEN:
    print("✗ TELEGRAM_BOT_TOKEN not found in environment")
    exit(1)

print(f"Bot Token: {BOT_TOKEN[:20]}...")
print(f"Webhook URL: {WEBHOOK_URL}")
print()

# Set webhook
print("Setting webhook...")
telegram_api = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

payload = {
    "url": WEBHOOK_URL,
    "allowed_updates": ["message"],
    "drop_pending_updates": True
}

try:
    response = requests.post(telegram_api, json=payload)
    result = response.json()
    
    if result.get("ok"):
        print("✓ Webhook set successfully!")
        print()
        print(f"Webhook details:")
        print(json.dumps(result.get("result"), indent=2))
    else:
        print("✗ Failed to set webhook")
        print(result.get("description", "Unknown error"))
        exit(1)
        
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Get webhook info
print()
print("Fetching webhook info...")
telegram_api = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"

try:
    response = requests.get(telegram_api)
    result = response.json()
    
    if result.get("ok"):
        webhook_info = result.get("result", {})
        print()
        print("Current webhook configuration:")
        print(f"  URL: {webhook_info.get('url')}")
        print(f"  Has custom certificate: {webhook_info.get('has_custom_certificate')}")
        print(f"  Pending update count: {webhook_info.get('pending_update_count')}")
        print(f"  Last error date: {webhook_info.get('last_error_date')}")
        if webhook_info.get('last_error_message'):
            print(f"  Last error: {webhook_info.get('last_error_message')}")
    else:
        print("✗ Failed to get webhook info")
        print(result.get("description", "Unknown error"))
        
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 60)
print("Next steps:")
print("1. Add the bot to your Telegram group")
print("2. Send a test message to verify logging")
print("3. Check bot logs with: az functionapp log tail --name {} --resource-group <RG>".format(FUNCTION_APP_NAME))
print("=" * 60)
