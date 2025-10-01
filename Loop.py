# auto_mancing.py — Auto Fishing di Kampung Maifam
# Features:
#   - Kirim "mancing" → ditanya lokasi
#   - Ketik nama lokasi → bot looping kirim lokasi + klik "Tarik Alat Pancing"
#   - Pause/Resume/Stop manual
#
# Requirements:
#   pip install telethon python-dotenv

import os
import asyncio
import random
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------- config (.env) ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "KampungMaifamBot").lstrip('@')
OWNER_ID = int(os.getenv("OWNER_ID") or 0)

if not API_ID or not API_HASH or not PHONE:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE ter-set di kunci.env")

# ---------------- logging ----------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("fishing_bot")

# ---------------- client ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- state ----------------
lokasi_mancing = None
auto_mancing = False
paused = False

async def human_sleep(min_s=1.5, max_s=2.5):
    """Jeda random biar ga terlalu bot-like"""
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- main loop ----------------
async def mancing_loop():
    global lokasi_mancing, auto_mancing, paused
    while auto_mancing and lokasi_mancing:
        if paused:
            await asyncio.sleep(2)
            continue
        try:
            # 1. Kirim lokasi
            await client.send_message(BOT_USERNAME, lokasi_mancing)
            await human_sleep()

            # 2. Tunggu respon bot
            response = await client.wait_event(events.NewMessage(from_users=BOT_USERNAME))

            # 3. Cari tombol "Tarik Alat Pancing"
            if response.buttons:
                for row in response.buttons:
                    for button in row:
                        if "Tarik Alat Pancing" in button.text:
                            await human_sleep()
                            await button.click()
                            # tunggu hasil tangkapan
                            await client.wait_event(events.NewMessage(from_users=BOT_USERNAME))

            # Delay sebelum ulangi
            await human_sleep(3, 6)

        except asyncio.TimeoutError:
            print("⚠️ Timeout, ulangi...")
            await asyncio.sleep(3)
        except Exception as e:
            print("❌ Error loop:", e)
            await asyncio.sleep(5)

# ---------------- commands ----------------
@client.on(events.NewMessage(pattern='mancing', from_users=OWNER_ID))
async def start_mancing(event):
    global auto_mancing, lokasi_mancing
    lokasi_mancing = None
    auto_mancing = False
    await event.reply("Mancing dimana? 🎣")

@client.on(events.NewMessage(from_users=OWNER_ID))
async def owner_control(event):
    global auto_mancing, paused, lokasi_mancing
    msg = (event.raw_text or "").strip().lower()

    if lokasi_mancing is None and msg not in ["pause", "resume", "stop", "mancing"]:
        lokasi_mancing = event.raw_text.strip()
        auto_mancing = True
        paused = False
        await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
        client.loop.create_task(mancing_loop())

    elif msg == "pause":
        paused = True
        await event.reply("⏸ Auto-mancing dijeda")
    elif msg == "resume":
        paused = False
        await event.reply("▶️ Auto-mancing dilanjutkan")
    elif msg == "stop":
        auto_mancing = False
        lokasi_mancing = None
        await event.reply("⏹ Auto-mancing dihentikan")

# ---------------- startup ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    print(f">> Bot siap Auto Mancing di @{BOT_USERNAME}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
