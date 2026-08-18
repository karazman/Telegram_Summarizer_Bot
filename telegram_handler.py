"""
Telegram webhook handler and message processing.
"""

import os
import json
import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional
import telebot
from blob_storage import BlobMessageStorage


class TelegramHandler:
    """Handle Telegram webhook updates and message logging."""
    
    def __init__(
        self,
        bot_token: str,
        blob_storage: BlobMessageStorage,
        target_chat: str = "@jkbofewugfh98ewgfvbwoeitfhow",
        timezone: ZoneInfo = ZoneInfo("Europe/Vienna")
    ):
        """Initialize Telegram handler."""
        self.bot = telebot.TeleBot(bot_token)
        self.blob_storage = blob_storage
        self.target_chat = target_chat
        self.target_username = target_chat.lstrip("@").lower()
        self.timezone = timezone
        
        # Register message handler
        @self.bot.message_handler(
            func=lambda message: True,
            content_types=["text"]
        )
        def log_message(message):
            self._handle_message(message)

    def _handle_message(self, message) -> None:
        """Process incoming message from Telegram."""
        # Only process messages from the configured group
        if message.chat.type not in ("group", "supergroup"):
            return

        chat_username = (message.chat.username or "").lower()
        if chat_username != self.target_username:
            return

        # Don't log bot commands
        if message.text.startswith("/"):
            return

        # Save message to blob storage
        self.save_message(message)

    def save_message(self, message) -> None:
        """Save message to blob storage."""
        username = (message.from_user.username or "").lower()
        now = datetime.datetime.now(self.timezone)

        message_data = {
            "chat_id": message.chat.id,
            "user_id": message.from_user.id,
            "username": username,
            "message": message.text,
            "date": now.isoformat(),
        }

        self.blob_storage.save_message(message_data)

        print(
            f"Logged message from @{message.from_user.username or 'unknown'}"
        )

    def process_update(self, update_data: Dict) -> None:
        """Process a Telegram update from webhook."""
        try:
            update = telebot.types.Update.de_json(update_data)
            self.bot.process_new_updates([update])
        except Exception as e:
            print(f"Error processing Telegram update: {e}")

    def send_message(self, chat: str, text: str) -> None:
        """Send a message to a Telegram chat."""
        try:
            self.bot.send_message(chat, text)
            print(f"Message sent to {chat}")
        except Exception as e:
            print(f"Error sending message: {e}")

    def send_summary(self, summary: str) -> None:
        """Send daily summary to target group."""
        if not summary:
            return

        text = (
            "📊 Daily Summary — Last 24 Hours\n\n"
            f"{summary}"
        )

        self.send_message(self.target_chat, text)
