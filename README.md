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
   git clone https://github.com/Sirmirzaei/telegram-summarizer-bot.git
   cd telegram-summarizer-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the bot:**
   - Replace `YOUR_BOT_TOKEN` in `telegram_bot.py` with your Telegram Bot Token.

4. **Run the bot:**
   ```bash
   python telegram_bot.py
   ```

## Requirements
- Python 3.7+
- `pyTelegramBotAPI`
- `transformers`
- `pandas`
- `torch` or `tensorflow`

## Deployment
To keep the bot running continuously on a server, use:
```sh
nohup python telegram_bot.py &
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author
👨‍💻 **Mehran Mirzaei**  
📧 Connect on [LinkedIn](https://www.linkedin.com/in/mehran-mirzaei)  
💻 Open to contributions & improvements! 🚀  


