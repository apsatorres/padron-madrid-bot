#!/usr/bin/env python3
"""
Debug: Test sending messages via Telegram.
Run: python tests/test_telegram.py
"""

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.notifier import send_notification

print("Testing Telegram connection...")
print("=" * 60)

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not configured in .env")
    exit(1)

if not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_CHAT_ID not configured in .env")
    print("\nTo get it:")
    print("1. Send a message to your bot on Telegram")
    print(f"2. Visit: https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates")
    print("3. Look for 'chat':{'id':XXXXXXX} - that's your CHAT_ID")
    exit(1)

print(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
print(f"Chat ID: {TELEGRAM_CHAT_ID}")
print("-" * 60)

if send_notification("Bot de citas Madrid - Connection test OK!"):
    print("\nMessage sent! Check Telegram.")
else:
    print("\nERROR sending message.")
