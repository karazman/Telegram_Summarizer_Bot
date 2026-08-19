# Telegram Summarizer Bot - Azure Functions

Telegram bot that summarizes group chat messages from the last 24 hours using BART ML model and runs on Azure Functions.

## Features

✅ Logs messages from Telegram group chat
✅ Summarizes messages from the last 24 hours using BART ML
✅ Automatic daily summary at 20:00 Europe/Vienna via Timer Trigger
✅ Webhook-based update processing (no long-polling)
✅ Messages stored in Azure Blob Storage (persistent, scalable)
✅ Priority weighting for configured users (@Michael_Schredl)
✅ Serverless architecture - runs on Azure App Service Plan

## Architecture

### Azure Functions Triggers

1. **HTTP Trigger** (`/api/telegram`)
   - Receives Telegram webhook updates
   - Processes and logs incoming messages
   - Stores messages in Azure Blob Storage

2. **Timer Trigger** (hourly check, execution at 20:00 Europe/Vienna)
   - Generates summary from last 24 hours
   - Sends summary to Telegram group

3. **HTTP Trigger** (`/api/trigger-summary`)
   - Manual summary trigger for testing
   - Requires authentication token

### Storage

- **Azure Blob Storage**: Message persistence
- **Blob structure**: `messages/{chat_id}/YYYY/MM/DD/{timestamp}_{user_id}.json`

## Prerequisites

- Python 3.9+
- Azure Storage Account
- Azure Functions runtime
- Telegram Bot Token
- Target Telegram group with bot added

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/karazman/Telegram_Summarizer_Bot.git
cd Telegram_Summarizer_Bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `local.settings.json`:

```bash
cp .env.example local.settings.json
```

Edit `local.settings.json` with your values:

```json
{
  "Values": {
    "TELEGRAM_BOT_TOKEN": "your_bot_token",
    "AZURE_STORAGE_CONNECTION_STRING": "your_connection_string",
    "TARGET_CHAT": "@your_group_username",
    "TARGET_CHAT_ID": "123456789",
    "PRIORITY_USERNAME": "michael_schredl",
    "MAX_DAILY_MESSAGES": "500",
    "TIMEZONE": "Europe/Vienna",
    "ADMIN_AUTH_TOKEN": "your_secret_token"
  }
}
```

### 4. Local Testing

```bash
func start
```

The functions will be available at:
- Webhook: `http://localhost:7071/api/telegram`
- Manual trigger: `http://localhost:7071/api/trigger-summary`
- Health check: `http://localhost:7071/api/health`

### 5. Deploy to Azure

```bash
# Create Azure Function App (one time)
az functionapp create --resource-group <RG_NAME> \
  --consumption-plan-location <REGION> \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name <FUNCTION_APP_NAME>

# Deploy code
func azure functionapp publish <FUNCTION_APP_NAME>
```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | `123456:ABC-...` |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection | `DefaultEndpointsProtocol=...` |
| `TARGET_CHAT` | Target group username | `@jkbofewugfh98ewgfvbwoeitfhow` |
| `TARGET_CHAT_ID` | Telegram chat ID | `1234567890` |
| `PRIORITY_USERNAME` | Username to prioritize | `michael_schredl` |
| `TIMEZONE` | Timezone for scheduling | `Europe/Vienna` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DAILY_MESSAGES` | 500 | Max messages to summarize |
| `ADMIN_AUTH_TOKEN` | (required) | Token for manual trigger endpoint |

## Telegram Webhook Setup

Set webhook in Telegram to point to your Azure Function:

```bash
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<FUNCTION_APP>.azurewebsites.net/api/telegram"}'
```

## File Structure

```
├── function_app.py           # Azure Functions entry point
├── telegram_handler.py       # Telegram webhook processing
├── summarizer.py             # BART summarization logic
├── blob_storage.py           # Azure Blob Storage integration
├── requirements.txt          # Python dependencies
├── local.settings.json       # Local configuration
├── .env.example              # Configuration template
└── README.md                 # This file
```

## API Endpoints

### POST /api/telegram
Receives Telegram webhook updates

**Request**: Telegram update JSON
**Response**: `{"ok": true}`

### POST /api/trigger-summary
Manual summary trigger

**Request**:
```json
{
  "auth_token": "your_secret_token"
}
```

**Response**:
```json
{
  "ok": true,
  "summary": "..."
}
```

### GET /api/health
Health check

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

## How It Works

1. **Message Logging**
   - Telegram sends updates to HTTP webhook
   - Messages are parsed and stored in Azure Blob Storage
   - Each message: timestamp, username, text, user ID

2. **Summarization**
  - Timer checks hourly and runs at 20:00 Europe/Vienna
   - Loads all messages from last 24 hours
   - Uses BART model to generate summary
   - Priority messages (@Michael_Schredl) weighted higher if limit reached

3. **Summary Delivery**
   - Formatted summary sent to Telegram group
   - Includes 2-3 paragraph overview

## Performance Considerations

- **BART Model**: ~1-2 GB memory, first load takes ~30 seconds
- **Message Storage**: Blob Storage scales automatically
- **Summarization Time**: Depends on message count (500 messages ~2-3 minutes)
- **Premium Plan Recommended**: For consistent performance with large message volumes

## Troubleshooting

### Messages not being logged
- Check Telegram bot permissions in group
- Verify `TARGET_CHAT` and `TARGET_CHAT_ID` match your group
- Check webhook URL is configured correctly in Telegram

### Summary generation fails

`facebook/bart-large-cnn` is a general summarization model, not an
instruction-tuned moderator model. The application therefore calculates
participant counts, topic groupings, and source-backed action signals before
inference. This reduces message-by-message output and avoids fabricated
consensus, but nuanced agreement or disagreement can still be imperfect.
- Check bot has sufficient memory/timeout (Azure Premium Plan recommended)
- Verify Azure Storage connection string is valid
- Check for sufficient permissions on Blob Storage

### Timezone issues
- Verify `TIMEZONE` environment variable
- Timer trigger uses UTC, app converts to configured timezone

## License

MIT

## Support

For issues or questions, open an issue on GitHub.
