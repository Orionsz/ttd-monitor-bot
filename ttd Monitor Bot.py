import requests
from bs4 import BeautifulSoup
import telegram
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from datetime import datetime, timedelta
import asyncio

# Telegram Bot Token and chat ID
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID_HERE'

# URL for the login page
login_url = "http://www.ttdsales.com/66bit/login.php"

# URL for the page containing the workers information after login
data_url = "http://www.ttdsales.com/66bit/index.php"

# Login credentials
login_data = {
    'username': 'YOUR_USERNAME_HERE',
    'password': 'YOUR_PASSWORD_HERE'
}

# Create a Telegram bot instance
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Default settings
check_interval = 5  # in minutes
inactive_time_min = 30  # in minutes
inactive_time_max = 1440  # in minutes (24 hours)

# List to store ignored worker identifiers
ignored_workers = []

# Welcome message
welcome_message = (
    "🤖 *Welcome to the ttd Monitor Bot, made by Barny Rubull!*\n\n"
    "ℹ️ This bot monitors workers and sends notifications if they become inactive based on specified parameters.\n"
    "It will not send any messages if all workers are functioning normally.\n\n"
    "Here are the available commands:\n\n"
    "🔧 `/ig <worker_number(s)>` - Ignore workers by Clore number (e.g., `/ig 348063` will ignore all workers with that Clore number)\n"
    "🔧 `/igall <hours>` - Ignore all workers inactive for more than a certain number of hours (e.g., `/igall 3`, default 24)\n"
    "⏱️ `/checkinterval <minutes>` - Set the interval for checks (1 to 120 minutes, default 5)\n"
    "⏰ `/inactive <minutes>` - Set the inactivity threshold (5 to 180 minutes, default 30)\n"
    "ℹ️ `/start` or `/help` - Show this help message again"
)

# Flag to track if the welcome message has been sent
welcome_message_sent = False

# Function to convert the "Last Seen" time from format "23h 14m 36s" to a timedelta object
def parse_last_seen(time_str):
    h, m, s = 0, 0, 0
    time_parts = time_str.split()
    for part in time_parts:
        if 'h' in part:
            h = int(part.replace('h', ''))
        elif 'm' in part:
            m = int(part.replace('m', ''))
        elif 's' in part:
            s = int(part.replace('s', ''))
    return timedelta(hours=h, minutes=m, seconds=s)

# Function to check if the "Last Seen" format is valid
def is_valid_last_seen_format(time_str):
    try:
        if 'h' in time_str or 'm' in time_str or 's' in time_str:
            parse_last_seen(time_str)
            return True
    except ValueError:
        return False
    return False

# Function to check the status of the workers
async def check_servers():
    global welcome_message_sent
    print("Checking servers...")  # Debugging message
    with requests.Session() as session:
        # Perform the login
        response = session.post(login_url, data=login_data)

        # Check if login was successful
        if response.url != login_url:
            print("Login successful!")
            # Access the page with the required data
            data_page = session.get(data_url)
            print("Data page retrieved, parsing workers...")  # Debugging message
            soup = BeautifulSoup(data_page.content, 'html.parser')

            # Send welcome message only on the first check
            if not welcome_message_sent:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=welcome_message, parse_mode="Markdown")
                welcome_message_sent = True

            # Extract information about each worker (depends on the structure of the website)
            workers = soup.find_all('tr')

            inactive_workers = []
            current_time = datetime.now()

            for worker in workers:
                columns = worker.find_all('td')
                if len(columns) < 5:
                    continue
                worker_id = columns[0].text.strip()
                worker_name = columns[1].text.strip()
                last_seen = columns[4].text.strip()

                # Extract the Clore number from the worker's name
                clore_number = worker_name.split('-')[1] if 'Clore-' in worker_name else None

                if not clore_number:
                    print(f"Could not extract Clore number from worker name: {worker_name}")
                    continue

                # Debugging output
                print(f"Worker: {worker_name}, Last Seen: {last_seen}")

                if is_valid_last_seen_format(last_seen):
                    try:
                        last_seen_delta = parse_last_seen(last_seen)
                        time_since_last_seen = datetime.now() - datetime.now() + last_seen_delta
                    except ValueError as e:
                        print(f"Error parsing time for worker {worker_name}: {e}")
                        continue
                else:
                    print(f"Unexpected format for last_seen: {last_seen}")
                    continue

                # Check if last seen is between 30 minutes and 24 hours ago
                if timedelta(minutes=inactive_time_min) <= time_since_last_seen <= timedelta(minutes=inactive_time_max):
                    # Ignore workers if their Clore number is in the ignored list
                    if clore_number not in ignored_workers:
                        inactive_workers.append((worker_id, worker_name, last_seen))

            if inactive_workers:
                for worker_id, worker_name, last_seen in inactive_workers:
                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"💤 Worker {worker_name} (ID: {worker_id}) has been inactive for {last_seen} ⌛."
                    )
            else:
                print("No inactive workers found in the specified time range.")
        else:
            print("Login failed. Please check your credentials or login URL.")

# Function to ignore specific workers by their Clore number
async def ignore_worker(update, context: CallbackContext):
    if len(context.args) > 0:
        clore_numbers = context.args[0].split(',')
        for clore_number in clore_numbers:
            clore_number = clore_number.strip()
            ignored_workers.append(clore_number)
            await update.message.reply_text(f"Workers with Clore number {clore_number} are now ignored.")
    else:
        await update.message.reply_text("Please provide Clore numbers to ignore, separated by commas.")

# Function to ignore all workers inactive for a given time
async def ignore_all_workers(update, context: CallbackContext):
    try:
        hours = int(context.args[0]) if len(context.args) > 0 else 24  # Default to 24 hours if no argument is given
        if 1 <= hours <= 24:
            print(f"Ignoring all workers inactive for more than {hours} hours.")
            threshold = timedelta(hours=hours)

            with requests.Session() as session:
                response = session.post(login_url, data=login_data)

                if response.url != login_url:
                    data_page = session.get(data_url)
                    soup = BeautifulSoup(data_page.content, 'html.parser')
                    workers = soup.find_all('tr')

                    for worker in workers:
                        columns = worker.find_all('td')
                        if len(columns) < 5:
                            continue
                        worker_id = columns[0].text.strip()
                        worker_name = columns[1].text.strip()
                        last_seen = columns[4].text.strip()

                        print(f"Worker: {worker_name}, Last Seen: {last_seen}")

                        if is_valid_last_seen_format(last_seen):
                            try:
                                last_seen_delta = parse_last_seen(last_seen)
                            except ValueError as e:
                                print(f"Error parsing time for worker {worker_name}: {e}")
                                continue

                            if last_seen_delta > threshold:
                                clore_number = worker_name.split('-')[1] if 'Clore-' in worker_name else None
                                if clore_number:
                                    # Only ignore workers that are currently inactive for more than the specified hours
                                    if clore_number not in ignored_workers:
                                        ignored_workers.append(clore_number)
                                        print(f"Ignored workers with Clore number {clore_number}")
                    await update.message.reply_text(f"Ignored all workers inactive for more than {hours} hours.")
                else:
                    await update.message.reply_text("Login failed. Please check your credentials or login URL.")
        else:
            await update.message.reply_text("Please provide a value between 1 and 24 hours.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

# Function to set check interval
async def set_check_interval(update, context: CallbackContext):
    global check_interval
    if len(context.args) > 0:
        try:
            interval = int(context.args[0])
            if 1 <= interval <= 120:
                check_interval = interval
                await update.message.reply_text(f"Check interval set to {check_interval} minutes.")
                await check_servers()  # Immediately run a check after setting the interval
            else:
                await update.message.reply_text("Please provide a value between 1 and 120 minutes.")
        except ValueError:
            await update.message.reply_text("Please provide a valid number.")
    else:
        await update.message.reply_text("Please provide the check interval in minutes.")

# Function to set inactive time
async def set_inactive_time(update, context: CallbackContext):
    global inactive_time_min
    if len(context.args) > 0:
        try:
            time_inactive = int(context.args[0])
            if 5 <= time_inactive <= 180:
                inactive_time_min = time_inactive
                await update.message.reply_text(f"Inactive time set to {inactive_time_min} minutes.")
            else:
                await update.message.reply_text("Please provide a value between 5 and 180 minutes.")
        except ValueError:
            await update.message.reply_text("Please provide a valid number.")
    else:
        await update.message.reply_text("Inactive time reset to default of 30 minutes.")
        inactive_time_min = 30

# Function to handle unknown commands
async def unknown_command(update, context: CallbackContext):
    await update.message.reply_text(
        "Unknown command. Please use one of the following:\n"
        "/checkinterval\n"
        "/inactive\n"
        "/ig\n"
        "/igall"
    )

# Start/help command to show the welcome message
async def start(update, context: CallbackContext):
    print("Received /start or /help command")  # Debugging message
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Asynchronous function to repeatedly check servers
async def scheduled_check():
    while True:
        await check_servers()
        print("Sleeping for", check_interval, "minutes")  # Debugging message
        await asyncio.sleep(check_interval * 60)  # Convert minutes to seconds

# Main function to set up the bot and handlers
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("ig", ignore_worker))
    application.add_handler(CommandHandler("igall", ignore_all_workers))
    application.add_handler(CommandHandler("checkinterval", set_check_interval))
    application.add_handler(CommandHandler("inactive", set_inactive_time))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    # Add handler for unknown commands
    application.add_handler(MessageHandler(filters.Command, unknown_command))

    print("Starting bot...")
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_check())
    application.run_polling()
    print("Bot started successfully!")

if __name__ == '__main__':
    print("Running main function...")
    main()
