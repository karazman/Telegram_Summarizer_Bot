# Azure Functions Telegram Bot - Deployment Checklist

## Pre-Deployment Checklist

### Requirements
- [ ] Python 3.9+ installed
- [ ] Azure CLI installed (`az` command available)
- [ ] Azure Functions Core Tools installed (`func` command available)
- [ ] Git installed
- [ ] Active Azure subscription
- [ ] Telegram bot created (@BotFather)

### Configuration
- [ ] Telegram Bot Token obtained
- [ ] Target group created on Telegram
- [ ] Bot added to target group with admin permissions
- [ ] Target Chat ID known (use `setup_webhook.py` to find it)
- [ ] Azure Storage Account created or planned
- [ ] Resource Group decided (e.g., `telegram-bot-rg`)
- [ ] Function App name decided (e.g., `telegram-summarizer-bot`)

## Local Development Checklist

### Setup
- [ ] Repository cloned: `git clone <repo>`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Environment configured: Copy `.env.example` → `local.settings.json`
- [ ] Fill in all required secrets in `local.settings.json`

### Testing
- [ ] Run local Azure Functions: `func start`
- [ ] Run test script: `python test_local.py`
- [ ] Health check passes: `curl http://localhost:7071/api/health`
- [ ] Webhook endpoint responds: `curl -X POST http://localhost:7071/api/telegram -H "Content-Type: application/json" -d '{}'`
- [ ] Manual summary trigger works: `curl -X POST http://localhost:7071/api/trigger-summary -H "Content-Type: application/json" -d '{"auth_token": "YOUR_TOKEN"}'`

## Azure Deployment Checklist

### Infrastructure
- [ ] Azure Resource Group created: `az group create --name <RG_NAME> --location <REGION>`
- [ ] Storage Account created: `az storage account create ...`
- [ ] Storage container created: `az storage container create --name telegram-messages`
- [ ] Function App created: `az functionapp create ...`

### Configuration
- [ ] Environment variables set in Azure:
  - [ ] `TELEGRAM_BOT_TOKEN`
  - [ ] `AZURE_STORAGE_CONNECTION_STRING`
  - [ ] `TARGET_CHAT`
  - [ ] `TARGET_CHAT_ID`
  - [ ] `PRIORITY_USERNAME`
  - [ ] `TIMEZONE`
  - [ ] `ADMIN_AUTH_TOKEN`
  - [ ] `MAX_DAILY_MESSAGES`

- [ ] Set with: 
  ```bash
  az functionapp config appsettings set --name <APP_NAME> --resource-group <RG_NAME> --settings KEY1=VALUE1 KEY2=VALUE2 ...
  ```

### Deployment
- [ ] Code deployed: `func azure functionapp publish <APP_NAME>`
- [ ] Deployment completed without errors
- [ ] Check deployment: `az functionapp deployment list-publishing-credentials --name <APP_NAME> --resource-group <RG_NAME>`

### Verification
- [ ] Health check accessible: `curl https://<APP_NAME>.azurewebsites.net/api/health`
- [ ] Webhook URL format: `https://<APP_NAME>.azurewebsites.net/api/telegram`
- [ ] Set Telegram webhook: `python setup_webhook.py`
- [ ] Webhook configuration verified on Telegram API

## Post-Deployment Checklist

### Testing
- [ ] Send test message in Telegram group
- [ ] Check Azure Functions logs: `az functionapp log tail --name <APP_NAME> --resource-group <RG_NAME>`
- [ ] Verify message logged in Blob Storage
- [ ] Manually trigger summary: See webhook setup instructions
- [ ] Summary sent to group successfully

### Monitoring
- [ ] Enable Application Insights (optional but recommended):
  ```bash
  az functionapp config set --name <APP_NAME> --resource-group <RG_NAME> --enable-insights
  ```
- [ ] Check Application Insights in Azure Portal
- [ ] Monitor function execution time and errors
- [ ] Set up alerts for failures

### Maintenance
- [ ] Schedule blob storage cleanup (done automatically in daily summary)
- [ ] Monitor storage costs
- [ ] Review logs regularly for errors
- [ ] Keep BART model updated (in requirements.txt)

## Troubleshooting Checklist

### Messages not logging
- [ ] Bot has Send Messages permission in group
- [ ] `TARGET_CHAT_ID` matches actual group ID
- [ ] Webhook is properly configured
- [ ] Check function logs for errors

### Summary not generating
- [ ] BART model has enough memory (recommend Premium Plan)
- [ ] Message count < `MAX_DAILY_MESSAGES`
- [ ] Timer trigger timezone matches expectation
- [ ] Check Application Insights for timeouts

### Deployment issues
- [ ] Python version matches (3.9+)
- [ ] All dependencies in requirements.txt
- [ ] local.settings.json not committed (in .gitignore)
- [ ] Azure CLI authenticated: `az login`

## Quick Reference Commands

```bash
# View logs
az functionapp log tail --name <APP_NAME> --resource-group <RG_NAME>

# View app settings
az functionapp config appsettings list --name <APP_NAME> --resource-group <RG_NAME>

# Update app settings
az functionapp config appsettings set --name <APP_NAME> --resource-group <RG_NAME> --settings KEY=VALUE

# Restart function app
az functionapp restart --name <APP_NAME> --resource-group <RG_NAME>

# Delete resources
az group delete --name <RG_NAME>

# Check webhook
curl -X POST https://api.telegram.org/bot<TOKEN>/getWebhookInfo | jq
```

## Support & Issues

- Check Azure Functions documentation: https://docs.microsoft.com/azure/azure-functions/
- Check Telegram Bot API docs: https://core.telegram.org/bots/api
- Check logs in Azure Portal (Azure Functions > <APP_NAME> > Monitor)
