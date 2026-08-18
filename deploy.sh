#!/bin/bash
# Deployment script for Azure Functions

set -e

echo "=== Telegram Summarizer Bot - Azure Functions Deployment ==="
echo

# Check prerequisites
echo "Checking prerequisites..."

command -v az >/dev/null 2>&1 || { echo "Azure CLI not found. Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"; exit 1; }
command -v func >/dev/null 2>&1 || { echo "Azure Functions Core Tools not found. Install from https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"; exit 1; }

echo "✓ Azure CLI installed"
echo "✓ Azure Functions Core Tools installed"
echo

# Get configuration
read -p "Enter Azure Resource Group name: " RESOURCE_GROUP
read -p "Enter Azure Region (e.g., westeurope): " REGION
read -p "Enter Function App name: " FUNCTION_APP_NAME
read -p "Enter Storage Account name: " STORAGE_ACCOUNT
read -p "Enter Telegram Bot Token: " BOT_TOKEN
read -p "Enter Target Chat ID: " TARGET_CHAT_ID
read -s -p "Enter Admin Auth Token: " ADMIN_TOKEN
echo

# Create resource group
echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$REGION"

# Create storage account
echo "Creating storage account..."
az storage account create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$STORAGE_ACCOUNT" \
  --location "$REGION" \
  --sku Standard_LRS

# Get storage connection string
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group "$RESOURCE_GROUP" \
  --name "$STORAGE_ACCOUNT" \
  --query connectionString -o tsv)

# Create container in blob storage
echo "Creating blob container..."
az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name telegram-messages

# Create Function App
echo "Creating Azure Function App..."
az functionapp create \
  --resource-group "$RESOURCE_GROUP" \
  --consumption-plan-location "$REGION" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name "$FUNCTION_APP_NAME" \
  --os-type Linux

# Configure app settings
echo "Configuring app settings..."
az functionapp config appsettings set \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    TELEGRAM_BOT_TOKEN="$BOT_TOKEN" \
    AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION" \
    TARGET_CHAT_ID="$TARGET_CHAT_ID" \
    ADMIN_AUTH_TOKEN="$ADMIN_TOKEN" \
    PYTHON_ENABLE_WORKER_EXTENSIONS=1

# Deploy function code
echo "Deploying function code..."
func azure functionapp publish "$FUNCTION_APP_NAME"

# Get webhook URL
FUNCTION_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net/api/telegram"

echo
echo "=== Deployment Complete ==="
echo "Function App: $FUNCTION_APP_NAME"
echo "Webhook URL: $FUNCTION_URL"
echo
echo "Next steps:"
echo "1. Set Telegram webhook with:"
echo "   curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook -H 'Content-Type: application/json' -d '{\"url\": \"$FUNCTION_URL\"}'"
echo "2. Add the bot to your Telegram group"
echo "3. Test manual summary trigger at:"
echo "   curl -X POST $FUNCTION_URL/trigger-summary -H 'Content-Type: application/json' -d '{\"auth_token\": \"$ADMIN_TOKEN\"}'"
