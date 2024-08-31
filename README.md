# TTD Monitor Bot

This Python script is a Telegram bot designed to monitor the activity of workers on the TTD platform. The bot checks the status of workers at regular intervals and sends notifications when a worker has been inactive for too long.

## Prerequisites

Before you can run the script, you need to have Python installed on your system. The required version is Python 3.6 or higher.

You also need to install the necessary Python libraries. You can do this by running the following command:

```bash
pip install requests beautifulsoup4 python-telegram-bot

Configuration
Before running the script, you need to configure the following information:

Telegram Bot Token: You need to obtain a bot token from BotFather on Telegram.
Telegram Chat ID: The chat ID where the bot will send notifications. You can obtain this by messaging your bot and checking the chat ID from the bot's response or using an online tool.
TTD Platform Login Credentials: You need to provide your username and password for the TTD platform.
Steps to Configure
Open the ttd_monitor.py file.
Replace the placeholder text with your actual credentials:
Replace 'YOUR_TELEGRAM_BOT_TOKEN_HERE' with your Telegram bot token.
Replace 'YOUR_TELEGRAM_CHAT_ID_HERE' with your Telegram chat ID.
Replace 'YOUR_USERNAME_HERE' and 'YOUR_PASSWORD_HERE' with your TTD platform login credentials.

Example:
TELEGRAM_BOT_TOKEN = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
TELEGRAM_CHAT_ID = '123456789'
login_data = {
    'username': 'your_username',
    'password': 'your_password'
}

Running the Bot
Once you have configured the script with your credentials, you can run the bot by executing the following command in your terminal:
python ttd Monitor Bot.py

The bot will start checking the status of your workers every 5 minutes (by default) and will notify you in Telegram if any worker has been inactive for the specified duration.

Available Commands
Once the bot is running, you can use the following commands in your Telegram chat with the bot:

/start - Show the help message with available commands.
/ig <worker_number> - Ignore a specific worker (e.g., /ig 343874).
/igall <hours> - Ignore all workers inactive for more than a certain number of hours (e.g., /igall 3, default 23).
/checkinterval <minutes> - Set the interval for checks (1 to 120 minutes, default 5).
/inactive <minutes> - Set the inactivity threshold (10 to 60 minutes, default 30).
Notes
The login_url and data_url in the script are already set for the TTD platform and do not need to be changed.
Make sure your bot has the necessary permissions to send messages in the specified chat.