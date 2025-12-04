import os
import json
import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
from telegram import Bot
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RESULT_PAGE = os.getenv("RESULT_PAGE")

bot = Bot(token=BOT_TOKEN)

# Files to track state & messages
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state.json"
MSG_FILE = BASE_DIR / "sent_messages.json"


# ---------- Helpers for state & message storage ----------

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"released": False}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def load_message_ids():
    if MSG_FILE.exists():
        try:
            with open(MSG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []


def save_message_ids(ids):
    with open(MSG_FILE, "w") as f:
        json.dump(ids, f)


# ---------- First-time CHAT_ID detection ----------

if not CHAT_ID:
    print("❗ CHAT_ID missing in .env → Auto-detecting…")
    updates = bot.get_updates()
    if updates:
        chat_id = updates[-1].message.chat_id
        print(f"\n📍 Your Chat ID: {chat_id}")
        print("👉 Paste this ID into CHAT_ID in .env and redeploy / rerun.\n")
    else:
        print("⚠ Send any message to your bot first, then rerun.")
    exit()


# ---------- Result link detection ----------

def detect_result_link():
    try:
        resp = requests.get(RESULT_PAGE, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Adjust this condition if needed when real link appears
        link = soup.find("a", href=True)
        if link and ("result" in link.text.lower() or "click" in link.text.lower()):
            return link["href"]
    except Exception as e:
        print("Error while checking result page:", e)
    return None


# ---------- Core jobs ----------

def check_result_status():
    state = load_state()
    if state.get("released"):
        print(f"[{datetime.now()}] Result already marked released. Skipping checks.")
        return schedule.CancelJob

    print(f"[{datetime.now()}] Checking result…")

    result_url = detect_result_link()
    if result_url:
        # Mark as released so we stop future checks & deletions
        state["released"] = True
        save_state(state)

        bot.send_message(chat_id=CHAT_ID, text="🎉 Results Published! Fetching your result now…")

        # Trigger scraper
        subprocess.Popen(["python", "src/result_scraper.py"])

        # Also clean up old 'not yet released' messages once
        delete_old_messages()

        return schedule.CancelJob
    else:
        # Not released → send status message and store its ID
        msg = bot.send_message(
            chat_id=CHAT_ID,
            text="⏳ Result Not Yet Released… Checking again in 5 mins."
        )
        msg_ids = load_message_ids()
        msg_ids.append(msg.message_id)
        save_message_ids(msg_ids)


def delete_old_messages():
    """
    Runs every day at 12:00.
    Deletes all 'not yet released' messages until result is released.
    """
    state = load_state()
    if state.get("released"):
        print(f"[{datetime.now()}] Result released. No more message cleanup needed.")
        return

    msg_ids = load_message_ids()
    if not msg_ids:
        print(f"[{datetime.now()}] No old status messages to delete.")
        return

    print(f"[{datetime.now()}] Deleting {len(msg_ids)} old status messages…")

    for mid in msg_ids:
        try:
            bot.delete_message(chat_id=CHAT_ID, message_id=mid)
        except Exception as e:
            # Ignore individual delete failures (e.g., too old / already deleted)
            print(f"Failed to delete message {mid}: {e}")

    # Clear list after deleting
    save_message_ids([])


# ---------- Main loop ----------

def main():
    bot.send_message(chat_id=CHAT_ID, text="🟢 Result Checker Active (5-min checks, noon cleanup)!")

    # Check every 5 minutes
    schedule.every(5).minutes.do(check_result_status)

    # Daily cleanup at 12:00 (server time)
    # If you want 12:00 IST and server is UTC, use "06:30" instead.
    schedule.every().day.at("6:30").do(delete_old_messages)

    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()
