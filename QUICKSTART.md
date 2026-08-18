# Quickstart: Telegram Summarizer Bot on Azure Functions

Fastest way to get your bot running on Azure Functions.

## 5-Minute Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example config
cp .env.example local.settings.json

# Edit with your values (use an editor like VS Code)
# Required: TELEGRAM_BOT_TOKEN, AZURE_STORAGE_CONNECTION_STRING
```

### 3. Run Locally
```bash
func start
```

The bot will be running at:
- Webhook: http://localhost:7071/api/telegram
- Health: http://localhost:7071/api/health
- Manual Trigger: http://localhost:7071/api/trigger-summary

### 4. Test (in another terminal)
```bash
python test_local.py
```

## 30-Minute Azure Deployment

### 1. Create Azure Resources
```bash
# Login to Azure
az login

# Create resource group
az group create --name telegram-bot-rg --location westeurope

# Create storage account
az storage account create \
  --name mybottgs$(date +%s) \
  --resource-group telegram-bot-rg \
  --location westeurope

# Create container
az storage container create \
  --account-name mybottgs<TIMESTAMP> \
  --name telegram-messages

# Get connection string
STORAGE_CONN=$(az storage account show-connection-string \
  --name mybottgs<TIMESTAMP> \
  --query connectionString -o tsv)
```

### 2. Create Function App
```bash
az functionapp create \
  --name telegram-summarizer-bot \
  --resource-group telegram-bot-rg \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux
```

### 3. Configure Settings
```bash
az functionapp config appsettings set \
  --name telegram-summarizer-bot \
  --resource-group telegram-bot-rg \
  --settings \
    TELEGRAM_BOT_TOKEN="123456:ABC-xyz" \
    AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
    TARGET_CHAT="@your_group_username" \
    TARGET_CHAT_ID="1234567890" \
    PRIORITY_USERNAME="michael_schredl" \
    TIMEZONE="Europe/Vienna" \
    ADMIN_AUTH_TOKEN="your_secret_token"
```

### 4. Deploy Code
```bash
func azure functionapp publish telegram-summarizer-bot
```

### 5. Set Telegram Webhook
```bash
# Get your webhook URL (replace with actual function app name)
WEBHOOK="https://telegram-summarizer-bot.azurewebsites.net/api/telegram"

# Set webhook
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK\"}"

# Verify
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo | jq
```

### 6. Test Deployment
```bash
# Health check
curl https://telegram-summarizer-bot.azurewebsites.net/api/health

# Trigger manual summary (replace with your token)
curl -X POST https://telegram-summarizer-bot.azurewebsites.net/api/trigger-summary \
  -H "Content-Type: application/json" \
  -d '{"auth_token": "your_secret_token"}'

# View logs
az functionapp log tail --name telegram-summarizer-bot --resource-group telegram-bot-rg
```

## How It Works

1. **Messages Incoming**
   - Telegram sends updates to your webhook
   - Bot logs messages to Azure Blob Storage

2. **Daily Summary (20:00 UTC)**
   - Timer trigger activates automatically
   - Loads messages from last 24 hours
   - BART AI generates summary
   - Summary sent to Telegram group

3. **Priority Users**
   - @michael_schredl messages weighted higher
   - If too many messages, his are kept first

## File Structure

```
├── function_app.py          ← Azure Functions entry point
├── telegram_handler.py      ← Webhook processing
├── summarizer.py            ← BART summarization
├── blob_storage.py          ← Azure storage integration
├── requirements.txt         ← Dependencies
├── local.settings.json      ← Local config (not committed)
├── README_AZURE.md          ← Full documentation
├── DEPLOYMENT_CHECKLIST.md  ← Detailed checklist
└── test_local.py            ← Local testing
```

## Configuration Reference

| Setting | Purpose | Example |
|---------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather | `123456:ABC-xyz` |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage connection | `DefaultEndpointsProtocol=...` |
| `TARGET_CHAT` | Group username | `@my_group_name` |
| `TARGET_CHAT_ID` | Group ID number | `1234567890` |
| `PRIORITY_USERNAME` | User to prioritize | `michael_schredl` |
| `TIMEZONE` | Your timezone | `Europe/Vienna` |
| `ADMIN_AUTH_TOKEN` | Secret for manual triggers | (any secure string) |

## Common Tasks

### View Logs
```bash
az functionapp log tail --name telegram-summarizer-bot --resource-group telegram-bot-rg
```

### Change Summary Time
Edit `function_app.py`, line with `@app.schedule()`:
```python
@app.schedule(schedule="0 20 * * *")  # Change 20 to your desired hour (UTC)
```

### Update a Setting
```bash
az functionapp config appsettings set \
  --name telegram-summarizer-bot \
  --resource-group telegram-bot-rg \
  --settings SETTING_NAME="new_value"
```

### Download Storage Data
```bash
az storage blob download \
  --account-name <storage_account> \
  --container-name telegram-messages \
  --name <blob_name> \
  --file /path/to/file
```

## Troubleshooting

**Q: Messages not logging**
- Ensure bot is admin in group
- Check `TARGET_CHAT_ID` is correct
- View logs: `az functionapp log tail ...`

**Q: Summary not generating**
- Verify BART has enough memory (use Premium Plan for safety)
- Check timer trigger in logs
- Test manually: `curl -X POST .../api/trigger-summary`

**Q: Webhook errors**
- Run: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Check URL is publicly accessible
- Verify Azure Function is running: `az functionapp list`

## Next Steps

- Set up [Application Insights](https://docs.microsoft.com/azure/azure-monitor/) for monitoring
- Configure [alerts](https://docs.microsoft.com/azure/azure-monitor/alerts/alerts-overview) for failures
- Review [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator/) for costs
- Read full [README_AZURE.md](README_AZURE.md) for advanced configuration

## Need Help?

1. Check the [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. Review [README_AZURE.md](README_AZURE.md) for detailed docs
3. Check Azure Portal logs
4. Run `python test_local.py` to validate local setup
