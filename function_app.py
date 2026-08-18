"""
Azure Functions for Telegram Summarizer Bot.

Triggers:
- HTTP: Receive Telegram webhook updates
- Timer: Generate and send daily summary at 20:00 UTC
"""

import os
import json
import azure.functions as func
from datetime import datetime
from zoneinfo import ZoneInfo

from blob_storage import BlobMessageStorage
from telegram_handler import TelegramHandler
from summarizer import MessageSummarizer


# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BLOB_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
TARGET_CHAT = os.environ.get("TARGET_CHAT", "@jkbofewugfh98ewgfvbwoeitfhow")
TARGET_CHAT_ID = int(os.environ.get("TARGET_CHAT_ID", "0"))
PRIORITY_USERNAME = os.environ.get("PRIORITY_USERNAME", "michael_schredl")
TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "Europe/Vienna"))
MAX_DAILY_MESSAGES = int(os.environ.get("MAX_DAILY_MESSAGES", "500"))

# Initialize services
blob_storage = BlobMessageStorage(BLOB_CONNECTION_STRING)
telegram_handler = TelegramHandler(BOT_TOKEN, blob_storage, TARGET_CHAT, TIMEZONE)
summarizer = MessageSummarizer(MAX_DAILY_MESSAGES, PRIORITY_USERNAME)

app = func.FunctionApp()


# =================================================================
# HTTP Trigger: Receive Telegram webhook updates
# =================================================================

@app.route(route="telegram", methods=["POST"])
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP webhook to receive Telegram bot updates.
    
    Telegram sends JSON updates to this endpoint.
    This function processes them and logs messages to blob storage.
    """
    try:
        update_data = req.get_json()
        
        print(f"Received Telegram update: {update_data.get('update_id')}")
        
        # Process the update
        telegram_handler.process_update(update_data)
        
        return func.HttpResponse(
            json.dumps({"ok": True}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        print(f"Error in telegram webhook: {e}")
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


# =================================================================
# Timer Trigger: Daily summary at 20:00 UTC
# =================================================================

@app.schedule(schedule="0 20 * * *")  # 20:00 UTC every day
def daily_summary_timer(mytimer: func.TimerRequest) -> None:
    """
    Timer trigger to generate and send daily summary.
    
    Runs at 20:00 UTC (equivalent to 20:00 Vienna time with UTC+1/+2).
    Summarizes messages from the last 24 hours.
    """
    utc_timestamp = datetime.utcnow().isoformat()
    
    print(f"Daily summary timer triggered at {utc_timestamp}")
    
    if mytimer.past_due:
        print("Timer is past due!")
    
    try:
        # Load messages from last 24 hours
        print("Loading messages from last 24 hours...")
        messages = blob_storage.load_messages_last_24_hours(TARGET_CHAT_ID, TIMEZONE)
        
        if not messages:
            print("No messages in the last 24 hours.")
            return
        
        print(f"Found {len(messages)} messages to summarize.")
        
        # Generate summary
        print("Generating summary...")
        summary = summarizer.summarize_messages(messages)
        
        if not summary:
            print("No usable messages to summarize.")
            return
        
        # Send summary
        print("Sending summary to Telegram...")
        telegram_handler.send_summary(summary)
        
        print("Daily summary completed successfully.")
        
        # Optional: Clean up old messages
        print("Cleaning up messages older than 30 days...")
        blob_storage.cleanup_old_messages(days_to_keep=30)
        
    except Exception as e:
        print(f"Error in daily summary timer: {e}")
        # Send error notification to chat
        error_msg = f"⚠️ Error generating daily summary: {str(e)}"
        telegram_handler.send_message(TARGET_CHAT, error_msg)


# =================================================================
# HTTP Trigger: Manual summary trigger (for testing)
# =================================================================

@app.route(route="trigger-summary", methods=["POST"])
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
        
        # Generate and send summary
        messages = blob_storage.load_messages_last_24_hours(TARGET_CHAT_ID, TIMEZONE)
        
        if not messages:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "No messages found"}),
                status_code=200,
                mimetype="application/json"
            )
        
        summary = summarizer.summarize_messages(messages)
        
        if not summary:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "Could not generate summary"}),
                status_code=200,
                mimetype="application/json"
            )
        
        telegram_handler.send_summary(summary)
        
        return func.HttpResponse(
            json.dumps({"ok": True, "summary": summary}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        print(f"Error in manual summary trigger: {e}")
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


# =================================================================
# Health check endpoint
# =================================================================

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }),
        status_code=200,
        mimetype="application/json"
    )
