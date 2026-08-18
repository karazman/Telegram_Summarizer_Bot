# Telegram Summarizer Bot 🤖📚

## About the Bot
This Telegram bot summarizes messages from a group chat based on a selected time range (e.g., last 12 hours, 1 day, 1 week). It uses machine learning (BART model) to generate concise summaries, making it easier for users to catch up on important discussions.

## Why I Built This Bot
I often miss out on reading all the messages in my group chats due to a busy schedule. This bot helps me stay informed by providing a summarized overview of key discussions over a selected period.

## Features
✅ Log messages from a Telegram group chat
✅ Summarize messages based on different time ranges: `12 hours`, `1 day`, `1 week`, etc.
✅ Uses a **machine learning model (BART)** for accurate summarization
✅ Supports **customizable summary lengths**

## How to Use
1. **Start the bot** by adding it to your group chat.
2. Use `/start` to see available time range options.
3. Use `/summarize <option>` to get a summary of messages for a specific time range.
   - Example: `/summarize 1day`

## Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/karazman/Telegram_Summarizer_Bot.git
   cd Telegram_Summarizer_Bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Function App:**
   - Set `TELEGRAM_BOT_TOKEN`, `TARGET_CHAT_ID`, `TARGET_CHAT`,
     `AZURE_STORAGE_CONNECTION_STRING`, and `AzureWebJobsStorage` as app settings.

4. **Run Azure Functions locally:**
   ```bash
   func start
   ```

## Requirements
- Python 3.11
- Azure Functions v4
- `pyTelegramBotAPI`
- `transformers`
- `torch`
- Azure Blob Storage and Queue Storage

## Deployment
Deploy `function_app.py` as an Azure Function App and configure Telegram to send
webhook updates to `POST /api/telegram`. See [README_AZURE.md](README_AZURE.md).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author
👨‍💻 **Mehran Mirzaei**
📧 Connect on [LinkedIn](https://www.linkedin.com/in/mehran-mirzaei)
💻 Open to contributions & improvements! 🚀


