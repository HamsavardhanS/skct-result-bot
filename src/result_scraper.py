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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Load .env file
env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RESULT_PAGE = os.getenv("RESULT_PAGE")
bot = Bot(token=BOT_TOKEN)

# First run → Detect Chat ID
if not CHAT_ID:
    print("❗ CHAT_ID missing in .env → Auto-detecting…")
    updates = bot.get_updates()
    if updates:
        chat_id = updates[-1].message.chat_id
        print(f"\n📍 Your Chat ID: {chat_id}")
        print("👉 Paste this ID inside .env under CHAT_ID and restart script.\n")
    else:
        print("⚠ Send any message to your bot first, then rerun")
    exit()

def detect_result_link():
    try:
        resp = requests.get(RESULT_PAGE)
        soup = BeautifulSoup(resp.text, "html.parser")
        link = soup.find("a", href=True)
        if link and ("result" in link.text.lower() or "click" in link.text.lower()):
            return link["href"]
    except:
        return None
    return None

def extract_result():
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )

    driver.get(RESULT_PAGE)
    time.sleep(3)

    try:
        # Step 1: Click the first result link
        result_link = driver.find_element(By.XPATH, "//a[contains(@href,'results')]")
        result_link.click()
        time.sleep(4)

        # Step 2: Switch to new tab
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)

        # Step 3: Fill login fields
        driver.find_element(By.NAME, "regno").send_keys(REGISTER_NO)
        driver.find_element(By.NAME, "dob").send_keys(DOB)
        driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
        time.sleep(4)

        # Step 4: Extract result
        result_text = driver.find_element(By.TAG_NAME, "body").text

        # Step 5: Notify user
        bot.send_message(chat_id=CHAT_ID, text=f"📊 RESULT:\n\n{result_text}")
        send_email("🎉 SKCT Result!", result_text)

        bot.send_message(chat_id=CHAT_ID, text="📨 Result also emailed!")

        print("🚀 RESULT FETCHED SUCCESSFULLY!")

    except Exception as e:
        print("⚠ ERROR AUTOMATING RESULT PAGE:", e)
        bot.send_message(chat_id=CHAT_ID, text="⚠ Error extracting result, will retry…")

    finally:
        driver.quit()


def main():
    bot.send_message(chat_id=CHAT_ID, text="🟢 Bot Activated: Result Monitor Running…")
    schedule.every(15).minutes.do(check_result_status)

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
