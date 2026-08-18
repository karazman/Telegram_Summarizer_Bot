"""
Telegram webhook handler and message processing.
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Callable, Dict, Optional
import telebot
from blob_storage import BlobMessageStorage


class TelegramHandler:
    """Handle Telegram webhook updates and message logging."""
    
    def __init__(
        self,
        bot_token: str,
        blob_storage: BlobMessageStorage,
        target_chat: str = "@jkbofewugfh98ewgfvbwoeitfhow",
        target_chat_id: int = 0,
        timezone: ZoneInfo = ZoneInfo("Europe/Vienna"),
        create_summary: Optional[Callable[[int], Optional[str]]] = None,
    ):
        """Initialize Telegram handler."""
        self.bot = telebot.TeleBot(bot_token)
        self.blob_storage = blob_storage
        self.target_chat = target_chat
        self.target_chat_id = target_chat_id
        self.target_username = target_chat.lstrip("@").lower()
        self.timezone = timezone
        self.create_summary = create_summary

        @self.bot.message_handler(commands=["dailysummary"])
        def daily_summary_command(message):
            self._handle_daily_summary(message)

        @self.bot.message_handler(
            func=lambda message: True,
            content_types=["text"]
        )
        def log_message(message):
            self._handle_message(message)

    def _is_target_group(self, message) -> bool:
        """Return whether a message belongs to the configured group."""
        if message.chat.type not in ("group", "supergroup"):
            return False

        if self.target_chat_id:
            return message.chat.id == self.target_chat_id

        chat_username = (message.chat.username or "").lower()
        return chat_username == self.target_username

    def _handle_daily_summary(self, message) -> None:
        """Generate and send the last 24 hours summary on demand."""
        if not self._is_target_group(message):
            return

        try:
            if self.create_summary is None:
                raise RuntimeError("Summary service is not configured")

            summary = self.create_summary(message.chat.id)

            if not summary:
                self.send_message(
                    message.chat.id,
                    "Keine Nachrichten in den letzten 24 Stunden gefunden.",
                )
                return

            self.send_summary(summary, message.chat.id)
        except Exception as error:
            print(f"Error handling /dailysummary: {error}")
            self.send_message(
                message.chat.id,
                "Die Zusammenfassung konnte nicht erstellt werden.",
            )

    def _handle_message(self, message) -> None:
        """Process incoming message from Telegram."""
        if not self._is_target_group(message):
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

    def send_message(self, chat: int | str, text: str) -> None:
        """Send a message to a Telegram chat."""
        try:
            self.bot.send_message(chat, text)
            print(f"Message sent to {chat}")
        except Exception as e:
            print(f"Error sending message: {e}")

    def send_summary(self, summary: str, chat: int | str | None = None) -> None:
        """Send daily summary to target group."""
        if not summary:
            return

        text = (
            "📊 Daily Summary — Last 24 Hours\n\n"
            f"{summary}"
        )

        self.send_message(chat or self.target_chat_id or self.target_chat, text)
