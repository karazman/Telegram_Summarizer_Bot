import os
import csv
import datetime
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from transformers import pipeline


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Test group
TARGET_CHAT = "@jkbofewugfh98ewgfvbwoeitfhow"
TARGET_USERNAME = TARGET_CHAT.lstrip("@").lower()

# Messages from this user receive preference if the daily chat
# is too large to fit into the summarization pipeline.
PRIORITY_USERNAME = "michael_schredl"

TIMEZONE = ZoneInfo("Europe/Vienna")

LOG_FILE = Path("group_messages.csv")

# Maximum number of messages processed for one daily summary.
# Priority-user messages are kept first if this limit is reached.
MAX_DAILY_MESSAGES = 500

bot = telebot.TeleBot(TOKEN)

print("Loading BART summarization model...")
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"
)
print("BART model loaded.")


# ---------------------------------------------------------
# Message storage
# ---------------------------------------------------------

csv_lock = threading.Lock()


def save_message(message):
    """Save a text message from the configured Telegram group."""

    username = (message.from_user.username or "").lower()

    now = datetime.datetime.now(TIMEZONE)

    row = {
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "username": username,
        "message": message.text,
        "date": now.isoformat(),
    }

    with csv_lock:
        file_exists = LOG_FILE.exists()

        with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "chat_id",
                    "user_id",
                    "username",
                    "message",
                    "date",
                ],
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)


def load_last_24_hours():
    """Return messages from the configured group from the last 24 hours."""

    if not LOG_FILE.exists():
        return []

    now = datetime.datetime.now(TIMEZONE)
    start = now - datetime.timedelta(hours=24)

    messages = []

    with csv_lock:
        with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    message_date = datetime.datetime.fromisoformat(row["date"])

                    if message_date.tzinfo is None:
                        message_date = message_date.replace(tzinfo=TIMEZONE)

                    if message_date >= start:
                        messages.append(
                            {
                                "username": row.get("username", "").lower(),
                                "message": row.get("message", ""),
                                "date": message_date,
                            }
                        )

                except (ValueError, KeyError):
                    continue

    messages.sort(key=lambda item: item["date"])

    return messages


# ---------------------------------------------------------
# Priority handling
# ---------------------------------------------------------

def select_messages(messages):
    """
    Keep all messages where possible.

    If there are too many messages, messages from Michael are retained
    preferentially. They are NOT labelled specially in the final text.
    """

    if len(messages) <= MAX_DAILY_MESSAGES:
        return messages

    priority = [
        msg
        for msg in messages
        if msg["username"] == PRIORITY_USERNAME
    ]

    others = [
        msg
        for msg in messages
        if msg["username"] != PRIORITY_USERNAME
    ]

    remaining_slots = max(
        0,
        MAX_DAILY_MESSAGES - len(priority)
    )

    # Prefer the most recent non-priority messages.
    selected = priority + others[-remaining_slots:]

    # Restore chronological order.
    selected.sort(key=lambda item: item["date"])

    return selected[-MAX_DAILY_MESSAGES:]


# ---------------------------------------------------------
# BART summarization
# ---------------------------------------------------------

def split_into_token_chunks(text, max_tokens=850):
    """Split text into chunks that BART can process safely."""

    tokenizer = summarizer.tokenizer

    token_ids = tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    )

    chunks = []

    for start in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[start:start + max_tokens]

        chunk_text = tokenizer.decode(
            chunk_ids,
            skip_special_tokens=True,
        )

        if chunk_text.strip():
            chunks.append(chunk_text)

    return chunks


def summarize_chunk(text, max_length=130, min_length=35):
    """Summarize one BART-sized piece of text."""

    result = summarizer(
        text,
        max_length=max_length,
        min_length=min_length,
        do_sample=False,
        truncation=True,
    )

    return result[0]["summary_text"].strip()


def summarize_messages(messages):
    """Create a compact multi-paragraph daily summary."""

    selected = select_messages(messages)

    # We intentionally don't add usernames to the BART input.
    # This means priority affects selection but doesn't visibly
    # single Michael out in the summary.
    transcript = "\n".join(
        msg["message"].strip()
        for msg in selected
        if msg["message"].strip()
        and not msg["message"].startswith("/")
    )

    if not transcript.strip():
        return None

    chunks = split_into_token_chunks(transcript)

    intermediate_summaries = []

    for index, chunk in enumerate(chunks, start=1):
        print(f"Summarizing chunk {index}/{len(chunks)}...")

        intermediate_summaries.append(
            summarize_chunk(
                chunk,
                max_length=130,
                min_length=30,
            )
        )

    combined = " ".join(intermediate_summaries)

    # If the intermediate result is still too long,
    # summarize it one more time.
    final_chunks = split_into_token_chunks(
        combined,
        max_tokens=850
    )

    if len(final_chunks) == 1:
        final_text = summarize_chunk(
            final_chunks[0],
            max_length=220,
            min_length=80,
        )
    else:
        condensed = [
            summarize_chunk(
                chunk,
                max_length=110,
                min_length=30,
            )
            for chunk in final_chunks
        ]

        combined_condensed = " ".join(condensed)

        final_chunk = split_into_token_chunks(
            combined_condensed,
            max_tokens=850
        )[0]

        final_text = summarize_chunk(
            final_chunk,
            max_length=220,
            min_length=80,
        )

    return format_as_paragraphs(final_text)


def format_as_paragraphs(text):
    """Format the generated summary into a few short paragraphs."""

    text = " ".join(text.split())

    sentences = []
    current = ""

    for char in text:
        current += char

        if char in ".!?":
            sentence = current.strip()

            if sentence:
                sentences.append(sentence)

            current = ""

    if current.strip():
        sentences.append(current.strip())

    if len(sentences) <= 2:
        return "\n\n".join(sentences)

    # Aim for roughly 3 short paragraphs.
    paragraph_count = min(3, len(sentences))
    paragraphs = [[] for _ in range(paragraph_count)]

    for index, sentence in enumerate(sentences):
        target = min(
            index * paragraph_count // len(sentences),
            paragraph_count - 1,
        )

        paragraphs[target].append(sentence)

    return "\n\n".join(
        " ".join(paragraph)
        for paragraph in paragraphs
        if paragraph
    )


# ---------------------------------------------------------
# Daily summary
# ---------------------------------------------------------

def create_and_send_daily_summary():
    """Generate and send the summary to the test group."""

    print("Creating daily summary...")

    messages = load_last_24_hours()

    if not messages:
        print("No messages in the last 24 hours.")
        return

    try:
        summary = summarize_messages(messages)

        if not summary:
            print("No usable messages to summarize.")
            return

        text = (
            "📊 Daily Summary — Last 24 Hours\n\n"
            f"{summary}"
        )

        bot.send_message(
            TARGET_CHAT,
            text,
        )

        print("Daily summary sent successfully.")

    except Exception as error:
        print(f"Error creating daily summary: {error}")


# ---------------------------------------------------------
# Telegram commands
# ---------------------------------------------------------

@bot.message_handler(commands=["start"])
def start_command(message):
    bot.reply_to(
        message,
        "🤖 Summarizer is running.\n\n"
        "The automatic daily summary is scheduled for "
        "20:00 Europe/Vienna.\n\n"
        "Use /dailysummary to test it manually."
    )


@bot.message_handler(commands=["dailysummary"])
def daily_summary_command(message):
    """Manually trigger the 24-hour summary for testing."""

    chat_username = (message.chat.username or "").lower()

    if chat_username != TARGET_USERNAME:
        bot.reply_to(
            message,
            "This command is only enabled in the configured test group."
        )
        return

    bot.reply_to(
        message,
        "⏳ Creating the summary of the last 24 hours..."
    )

    # Run BART outside Telegram's update-processing thread.
    thread = threading.Thread(
        target=create_and_send_daily_summary,
        daemon=True,
    )

    thread.start()


# ---------------------------------------------------------
# Log group messages
# ---------------------------------------------------------

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def log_message(message):
    """Store normal text messages from the configured test group."""

    if message.chat.type not in ("group", "supergroup"):
        return

    chat_username = (message.chat.username or "").lower()

    if chat_username != TARGET_USERNAME:
        return

    # Don't put bot commands into the summary source.
    if message.text.startswith("/"):
        return

    save_message(message)

    print(
        f"Logged message from "
        f"@{message.from_user.username or 'unknown'}"
    )


# ---------------------------------------------------------
# Scheduler
# ---------------------------------------------------------

scheduler = BackgroundScheduler(
    timezone=TIMEZONE
)

scheduler.add_job(
    create_and_send_daily_summary,
    trigger="cron",
    hour=20,
    minute=0,
    id="daily_summary",
    replace_existing=True,
)

scheduler.start()

print(
    "Daily summary scheduled for "
    "20:00 Europe/Vienna."
)


# ---------------------------------------------------------
# Start bot
# ---------------------------------------------------------

print(f"Bot running for {TARGET_CHAT}...")

bot.infinity_polling(
    timeout=30,
    long_polling_timeout=30,
)
