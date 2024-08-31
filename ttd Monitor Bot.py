import requests
from bs4 import BeautifulSoup
import time
import telegram
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime, timedelta
import asyncio

# Replace with your own values
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID_HERE'

# URL for the login page
login_url = "http://www.ttdsales.com/66bit/login.php"

# URL for the page containing the workers information after login
data_url = "http://www.ttdsales.com/66bit/index.php"

# Login credentials - replace with your own
login_data = {
    'username': 'YOUR_USERNAME_HERE',
    'password': 'YOUR_PASSWORD_HERE'
}

# Create a Telegram bot instance
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Default settings
check_interval = 5  # in minutes
inactive_time = 30  # in minutes by default

# List to store ignored workers
ignored_workers = []

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

            # Extract information about each worker (depends on the structure of the website)
            workers = soup.find_all('tr')  # Adjust according to the actual structure

            inactive_workers = []
            current_time = datetime.now()

            for worker in workers:
                # Assuming you have multiple columns: ID, Name, Ranges, Speed, Last Seen
                columns = worker.find_all('td')
                if len(columns) < 5:  # if there are not enough columns, skip this entry
                    continue
                worker_id = columns[0].text.strip()
                worker_name = columns[1].text.strip()
                last_seen = columns[4].text.strip()

                # Debugging output
                print(f"Worker: {worker_name}, Last Seen: {last_seen}")

                # Check if last_seen is in the correct format
                if is_valid_last_seen_format(last_seen):
                    try:
                        # Convert last_seen to a time difference (timedelta)
                        last_seen_delta = parse_last_seen(last_seen)
                    except ValueError as e:
                        print(f"Error parsing time for worker {worker_name}: {e}")
                        continue
                else:
                    print(f"Unexpected format for last_seen: {last_seen}")
                    continue

                # Check if more than inactive_time minutes have passed since last activity
                if last_seen_delta > timedelta(minutes=inactive_time) and worker_id not in ignored_workers:
                    inactive_workers.append((worker_id, worker_name, last_seen))

            if inactive_workers:
                for worker_id, worker_name, last_seen in inactive_workers:
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Worker {worker_name} (ID: {worker_id}) has not sent a solution in the last {inactive_time} minutes. Last seen {last_seen} ago.")
            else:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"All workers crack normally! Next check in {check_interval * 60} seconds.")
        else:
            print("Login failed. Please check your credentials or login URL.")

# Function to ignore specific workers
async def ignore_worker(update, context: CallbackContext):
    if len(context.args) > 0:
        worker_number = context.args[0]
        ignored_workers.append(worker_number)
        await update.message.reply_text(f"Worker {worker_number} is now ignored.")
    else:
        await update.message.reply_text("Please provide a worker number to ignore.")

# Function to ignore all workers inactive for a given time
async def ignore_all_workers(update, context: CallbackContext):
    try:
        hours = int(context.args[0]) if len(context.args) > 0 else 23  # Default to 23 hours if no argument is given
        if 1 <= hours <= 23:
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
                                ignored_workers.append(worker_id)
                                print(f"Ignored worker {worker_name} (ID: {worker_id})")
                    await update.message.reply_text(f"Ignored all workers inactive for more than {hours} hours.")
                else:
                    await update.message.reply_text("Login failed. Please check your credentials or login URL.")
        else:
            await update.message.reply_text("Please provide a value between 1 and 23 hours.")
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
            else:
                await update.message.reply_text("Please provide a value between 1 and 120 minutes.")
        except ValueError:
            await update.message.reply_text("Please provide a valid number.")
    else:
        await update.message.reply_text("Please provide the check interval in minutes.")

# Function to set inactive time
async def set_inactive_time(update, context: CallbackContext):
    global inactive_time
    if len(context.args) > 0:
        try:
            time_inactive = int(context.args[0])
            if 10 <= time_inactive <= 60:
                inactive_time = time_inactive
                await update.message.reply_text(f"Inactive time set to {inactive_time} minutes.")
            else:
                await update.message.reply_text("Please provide a value between 10 and 60 minutes.")
        except ValueError:
            await update.message.reply_text("Please provide a valid number.")
    else:
        await update.message.reply_text("Inactive time reset to default of 30 minutes.")
        inactive_time = 30

# Start command to initiate the bot
async def start(update, context: CallbackContext):
    print("Received /start command")  # Debugging message
    await update.message.reply_text(
        "🤖 *Welcome to the ttd Monitor Bot, made by Barny Rubull!*\n\n"
        "Here are the available commands:\n\n"
        "🔧 `/ig <worker_number>` - Ignore a specific worker (e.g., `/ig 343874`)\n"
        "🔧 `/igall <hours>` - Ignore all workers inactive for more than a certain number of hours (e.g., `/igall 3`, default 23)\n"
        "⏱️ `/checkinterval <minutes>` - Set the interval for checks (1 to 120 minutes, default 5)\n"
        "⏰ `/inactive <minutes>` - Set the inactivity threshold (10 to 60 minutes, default 30)\n"
        "ℹ️ `/start` - Show this help message again"
    )

# Asynchronous function to repeatedly check servers
async def scheduled_check():
    while True:
        await check_servers()
        print("Sleeping for", check_interval, "minutes")  # Debugging message
        await asyncio.sleep(check_interval * 60)  # Convert minutes to seconds

# Main function to set up the bot and handlers
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command to ignore a worker
    application.add_handler(CommandHandler("ig", ignore_worker))

    # Command to ignore all workers inactive for a specified time
    application.add_handler(CommandHandler("igall", ignore_all_workers))

    # Command to set check interval
    application.add_handler(CommandHandler("checkinterval", set_check_interval))

    # Command to set inactive time
    application.add_handler(CommandHandler("inactive", set_inactive_time))

    # Start command
    application.add_handler(CommandHandler("start", start))

    # Start the bot and the scheduled checks concurrently
    print("Starting bot...")
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_check())
    application.run_polling()
    print("Bot started successfully!")

if __name__ == '__main__':
    print("Running main function...")
    main()
