import os
import telebot
import pandas as pd
import datetime
from transformers import pipeline

# Replace with your bot token
TOKEN = "YOR_TELEGRAM_BOT_TOKEN"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# File to store group messages
LOG_FILE = "group_messages.csv"

# Predefined time intervals
TIME_INTERVALS = {
    "12hr": 12,
    "18hr": 18,
    "1day": 24,
    "2days": 48,
    "1week": 168,
}

# Load the Hugging Face summarization model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Command to start the bot
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Hello! You can summarize your messages in the group for a specific time range.\n\n"
        "Use: `/summarize <option>`\n\n"
        "*Available options:* \n"
        "- `12hr` (Last 12 hours)\n"
        "- `18hr` (Last 18 hours)\n"
        "- `1day` (Last 24 hours)\n"
        "- `2days` (Last 2 days)\n"
        "- `1week` (Last 7 days)\n\n"
        "Example: `/summarize 1day`"
    )

# Command to summarize messages based on selected time range
@bot.message_handler(commands=["summarize"])
def summarize_messages(message):
    user_id = message.from_user.id
    text = message.text.split()

    if len(text) != 2 or text[1] not in TIME_INTERVALS:
        bot.reply_to(
            message,
            "Invalid format. Use `/summarize <option>`\n\n"
            "Example: `/summarize 1day`"
        )
        return

    hours = TIME_INTERVALS[text[1]]
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(hours=hours)

    try:
        df = pd.read_csv(LOG_FILE)
        df["date"] = pd.to_datetime(df["date"])

        # Filter messages for the user within the time range
        user_messages = df[(df["user_id"] == user_id) & (df["date"] >= start_time)]

        if user_messages.empty:
            bot.reply_to(message, "No messages found in the selected time range.")
            return

        # Combine messages into one text block for summarization
        messages_text = " ".join(user_messages["message"].tolist())

        # Summarize messages (limit input size to avoid errors)
        if len(messages_text) > 1024:  # Adjusting for token limits
            messages_text = messages_text[:1024]

        summary = summarizer(messages_text, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]

        bot.reply_to(message, f"📊 *Summary for the last {text[1]}:*\n\n_{summary}_")

    except FileNotFoundError:
        bot.reply_to(message, "No messages found. Ensure message logging is enabled.")

# Function to log messages in the group
@bot.message_handler(func=lambda message: True, content_types=["text"])
def log_messages(message):
    """Logs all text messages from the group."""
    if message.chat.type in ["group", "supergroup"]:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        text = message.text
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Logging message: {username} ({user_id}) - {text}")  # Debugging

        # Save message to CSV
        df = pd.DataFrame([[user_id, username, text, date]], columns=["user_id", "username", "message", "date"])

        try:
            existing_df = pd.read_csv(LOG_FILE)
            df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            pass

        df.to_csv(LOG_FILE, index=False)

# Start the bot
print("Bot is running...")
bot.polling(none_stop=True)
