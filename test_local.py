#!/usr/bin/env python3
"""
Local testing script for Telegram Summarizer Bot.
Tests the Azure Functions without deploying.
"""

import json
import os
from dotenv import load_dotenv
from datetime import datetime
import requests

# Load environment variables
load_dotenv("local.settings.json")

# Configuration
LOCAL_URL = "http://localhost:7071/api"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_AUTH_TOKEN")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))

print("=" * 60)
print("Telegram Summarizer Bot - Local Test Script")
print("=" * 60)
print()

def test_health_check():
    """Test health check endpoint."""
    print("1. Testing health check endpoint...")
    try:
        response = requests.get(f"{LOCAL_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_telegram_webhook():
    """Test Telegram webhook with sample update."""
    print("\n2. Testing Telegram webhook...")
    
    # Sample Telegram update
    sample_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {
                "id": TARGET_CHAT_ID,
                "type": "supergroup",
                "username": "jkbofewugfh98ewgfvbwoeitfhow"
            },
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "text": "This is a test message from the bot."
        }
    }
    
    try:
        response = requests.post(
            f"{LOCAL_URL}/telegram",
            json=sample_update,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_manual_summary():
    """Test manual summary trigger."""
    print("\n3. Testing manual summary trigger...")
    
    payload = {
        "auth_token": ADMIN_TOKEN
    }
    
    try:
        response = requests.post(
            f"{LOCAL_URL}/trigger-summary",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Response: ok={result.get('ok')}, error={result.get('error', 'None')}")
        
        if result.get('ok') and result.get('summary'):
            print(f"\n   Summary preview:")
            print(f"   {result['summary'][:200]}...")
        
        return response.status_code == 200
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("Make sure the Azure Functions are running with: func start\n")
    input("Press Enter to start tests...")
    print()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Telegram Webhook", test_telegram_webhook()))
    results.append(("Manual Summary", test_manual_summary()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
