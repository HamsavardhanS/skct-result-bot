import os
import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
from telegram import Bot
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load .env from /config folder
env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RESULT_PAGE = os.getenv("RESULT_PAGE")

bot = Bot(token=BOT_TOKEN)

# Detect chat ID for first run
if not CHAT_ID:
    print("❗ CHAT_ID not set in .env — attempting auto-detect...\n")
    updates = bot.get_updates()
    if updates:
        chat_id = updates[-1].message.chat_id
        print(f"📍 Your Chat ID is: {chat_id}")
        print("👉 Copy this ID into your .env file under CHAT_ID and rerun script.\n")
    else:
        print("⚠ Please send any message to your bot in Telegram first, then run this script again.")
    exit()  # stop here until CHAT_ID is set

def detect_result_link():
    try:
        resp = requests.get(RESULT_PAGE)
        soup = BeautifulSoup(resp.text, "html.parser")
        link = soup.find("a", href=True)
        if link and "result" in link.text.lower():
            return link["href"]
    except:
        return None
    return None

def check_result_status():
    print(f"[{datetime.now()}] Checking result...")

    result_url = detect_result_link()
    if result_url:
        bot.send_message(chat_id=CHAT_ID, text="🎉 Result published online! Fetching your result now...")
        subprocess.Popen(["python", "result_scraper.py"])
        return schedule.CancelJob
    else:
        bot.send_message(chat_id=CHAT_ID, text="⏳ Result Not Yet Released. Checking again in 15 mins...")

def main():
    bot.send_message(chat_id=CHAT_ID, text="🟢 Result Checker Started!")
    schedule.every(15).minutes.do(check_result_status)

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
