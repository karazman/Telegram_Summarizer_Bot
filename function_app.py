"""
Azure Functions for Telegram Summarizer Bot.

Triggers:
- HTTP: Receive Telegram webhook updates
- Timer: Generate and send daily summary at 20:00 Europe/Vienna
"""

import json
import logging
import os
import threading
import azure.functions as func
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BLOB_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
TARGET_CHAT = os.environ.get("TARGET_CHAT", "@jkbofewugfh98ewgfvbwoeitfhow")
PRIORITY_USERNAME = os.environ.get("PRIORITY_USERNAME", "michael_schredl")
TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "Europe/Vienna"))


def get_int_setting(name: str, default: int) -> int:
    """Read an integer app setting without breaking function discovery."""
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        logging.error("App setting %s must be an integer.", name)
        return default


TARGET_CHAT_ID = get_int_setting("TARGET_CHAT_ID", 0)
MAX_DAILY_MESSAGES = get_int_setting("MAX_DAILY_MESSAGES", 500)

_services_lock = threading.RLock()
_blob_storage = None
_summarizer = None
_telegram_handler = None
_summary_queue = None


def get_blob_storage() -> "BlobMessageStorage":
    """Create the Blob Storage client only when a function needs it."""
    global _blob_storage

    if _blob_storage is None:
        with _services_lock:
            if _blob_storage is None:
                from blob_storage import BlobMessageStorage

                if not BLOB_CONNECTION_STRING:
                    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not configured")
                _blob_storage = BlobMessageStorage(BLOB_CONNECTION_STRING)

    return _blob_storage


def get_summarizer() -> "MessageSummarizer":
    """Create the summarizer without loading its model during discovery."""
    global _summarizer

    if _summarizer is None:
        with _services_lock:
            if _summarizer is None:
                from summarizer import MessageSummarizer

                _summarizer = MessageSummarizer(
                    MAX_DAILY_MESSAGES,
                    PRIORITY_USERNAME,
                )

    return _summarizer


def get_summary_queue():
    """Create the Azure Queue client used for on-demand summaries."""
    global _summary_queue

    if _summary_queue is None:
        with _services_lock:
            if _summary_queue is None:
                from azure.core.exceptions import ResourceExistsError
                from azure.storage.queue import QueueClient

                connection_string = os.environ.get("AzureWebJobsStorage")
                if not connection_string:
                    raise RuntimeError("AzureWebJobsStorage is not configured")

                _summary_queue = QueueClient.from_connection_string(
                    connection_string,
                    queue_name="daily-summary-requests",
                )
                try:
                    _summary_queue.create_queue()
                except ResourceExistsError:
                    pass

    return _summary_queue


def is_daily_summary_time(instant: datetime) -> bool:
    """Return whether an instant falls in the 20:00 Vienna hour."""
    return instant.astimezone(TIMEZONE).hour == 20


def create_daily_summary(chat_id: int) -> str | None:
    """Create a summary from the stored messages of the last 24 hours."""
    logging.info("Loading messages from last 24 hours.")
    messages = get_blob_storage().load_messages_last_24_hours(chat_id, TIMEZONE)

    if not messages:
        logging.info("No messages in the last 24 hours.")
        return None

    logging.info("Found %s messages to summarize.", len(messages))
    return get_summarizer().summarize_messages(messages)


def generate_and_send_daily_summary(
    chat_id: int,
    notify_if_empty: bool = False,
) -> str | None:
    """Generate and deliver a summary for one configured Telegram chat."""
    summary = create_daily_summary(chat_id)

    if summary:
        get_telegram_handler().send_summary(summary, chat_id)
    elif notify_if_empty:
        get_telegram_handler().send_message(
            chat_id,
            "Keine Nachrichten in den letzten 24 Stunden gefunden.",
        )

    return summary


def enqueue_daily_summary(chat_id: int) -> None:
    """Queue an on-demand summary without blocking the Telegram webhook."""
    get_summary_queue().send_message(json.dumps({"chat_id": chat_id}))


def get_telegram_handler() -> "TelegramHandler":
    """Create and configure Telegram handlers on first webhook use."""
    global _telegram_handler

    if _telegram_handler is None:
        with _services_lock:
            if _telegram_handler is None:
                from telegram_handler import TelegramHandler

                if not BOT_TOKEN:
                    raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
                if not TARGET_CHAT_ID:
                    raise RuntimeError("TARGET_CHAT_ID is not configured")
                _telegram_handler = TelegramHandler(
                    BOT_TOKEN,
                    get_blob_storage(),
                    TARGET_CHAT,
                    TARGET_CHAT_ID,
                    TIMEZONE,
                    enqueue_daily_summary,
                )

    return _telegram_handler

app = func.FunctionApp()


# =================================================================
# HTTP Trigger: Receive Telegram webhook updates
# =================================================================

@app.route(
    route="telegram",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP webhook to receive Telegram bot updates.
    
    Telegram sends JSON updates to this endpoint.
    This function processes them and logs messages to blob storage.
    """
    try:
        update_data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"ok": False, "error": "Invalid JSON payload"}),
            status_code=400,
            mimetype="application/json",
        )

    if not isinstance(update_data, dict) or "update_id" not in update_data:
        return func.HttpResponse(
            json.dumps({"ok": False, "error": "Invalid Telegram update"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        logging.info("Received Telegram update: %s", update_data["update_id"])
        get_telegram_handler().process_update(update_data)

        return func.HttpResponse(
            json.dumps({"ok": True}),
            status_code=200,
            mimetype="application/json",
        )
    except Exception:
        logging.exception("Error processing Telegram webhook update.")
        return func.HttpResponse(
            json.dumps({"ok": False, "error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )


# =================================================================
# Queue Trigger: Process on-demand Telegram summaries
# =================================================================

@app.queue_trigger(
    arg_name="message",
    queue_name="daily-summary-requests",
    connection="AzureWebJobsStorage",
)
def daily_summary_queue(message: func.QueueMessage) -> None:
    """Generate a queued /dailysummary request outside the HTTP webhook."""
    try:
        payload = message.get_json()
        chat_id = int(payload.get("chat_id", 0))

        if chat_id != TARGET_CHAT_ID:
            logging.warning("Ignoring summary request for an unconfigured chat.")
            return

        generate_and_send_daily_summary(chat_id, notify_if_empty=True)
    except Exception:
        logging.exception("Error processing queued daily summary.")
        try:
            get_telegram_handler().send_message(
                TARGET_CHAT_ID,
                "Die Zusammenfassung konnte nicht erstellt werden.",
            )
        except Exception:
            logging.exception("Could not send the summary error message to Telegram.")


# =================================================================
# Timer Trigger: Daily summary at 20:00 Europe/Vienna
# =================================================================

@app.schedule(
    schedule="0 0 * * * *",
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True,
)
def daily_summary_timer(mytimer: func.TimerRequest) -> None:
    """
    Timer trigger to generate and send daily summary.
    
    Azure invokes this function hourly in UTC. Summary generation only runs
    when that instant is 20:00 in Europe/Vienna, including daylight saving.
    """
    now_utc = datetime.now(timezone.utc)
    utc_timestamp = now_utc.isoformat()
    logging.info("Daily summary timer triggered at %s", utc_timestamp)

    if not is_daily_summary_time(now_utc):
        logging.info("Skipping timer outside 20:00 Europe/Vienna.")
        return
    
    if mytimer.past_due:
        logging.warning("Daily summary timer is past due.")
    
    try:
        summary = generate_and_send_daily_summary(TARGET_CHAT_ID)
        
        if not summary:
            logging.info("No usable messages to summarize.")
            return

        logging.info("Daily summary completed successfully.")
        get_blob_storage().cleanup_old_messages(days_to_keep=30)
    except Exception:
        logging.exception("Error in daily summary timer.")
        try:
            get_telegram_handler().send_message(
                TARGET_CHAT_ID,
                "Die automatische Zusammenfassung konnte nicht erstellt werden.",
            )
        except Exception:
            logging.exception("Could not send the timer error message to Telegram.")


# =================================================================
# HTTP Trigger: Manual summary trigger (for testing)
# =================================================================

@app.route(
    route="trigger-summary",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def trigger_summary_manual(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manual trigger for testing the summary generation.
    
    Expected POST body:
    {
        "auth_token": "<SECRET_TOKEN>"
    }
    """
    try:
        req_body = req.get_json()
        auth_token = req_body.get("auth_token")
        
        # Validate auth token
        expected_token = os.environ.get("ADMIN_AUTH_TOKEN")
        if not expected_token or auth_token != expected_token:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "Unauthorized"}),
                status_code=401,
                mimetype="application/json"
            )
        
        summary = generate_and_send_daily_summary(TARGET_CHAT_ID)
        
        if not summary:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "Could not generate summary"}),
                status_code=200,
                mimetype="application/json"
            )
        
        return func.HttpResponse(
            json.dumps({"ok": True, "summary": summary}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception:
        logging.exception("Error in manual summary trigger.")
        return func.HttpResponse(
            json.dumps({"ok": False, "error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


# =================================================================
# Health check endpoint
# =================================================================

@app.route(
    route="health",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }),
        status_code=200,
        mimetype="application/json"
    )
