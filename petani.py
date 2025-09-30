# petani.py
# Bot Farming Telegram (Maling + Kebun + Level Up EXP)
# Fitur:
#   - Auto maling (ambil kode curi uang)
#   - Auto kebun (tanam, siram, panen, repeat)
#   - Auto level up ketika EXP penuh
#   - EXP parsing otomatis dari semua pesan
#   - Start/Stop per fitur & Start/Stop all
#   - Status cek progress EXP
#   - Message Queue -> semua pesan lewat satu jalur aman
#
# Requirements:
#   pip install telethon python-dotenv

import os
import re
import time
import random
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------- CONFIG ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "GameBot").lstrip('@')
OWNER_ID = int(os.getenv("OWNER_ID") or 0)

if not API_ID or not API_HASH or not PHONE:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE ter-set di petani.env")

SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("Petani_session", API_ID, API_HASH)

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("petani")

# ---------------- STATE ----------------
running_maling = False
running_kebun = False
exp_current = 0
exp_max = 0

# ---------------- QUEUE ----------------
message_queue = asyncio.Queue()

async def safe_send(msg):
    """Masukkan pesan ke queue"""
    await message_queue.put(msg)

async def message_worker():
    """Worker kirim pesan satu-satu"""
    while True:
        msg = await message_queue.get()
        try:
            await client.send_message(BOT_USERNAME, msg)
            print(f"[SEND] {msg}")
        except Exception as e:
            print(f"[!] Gagal kirim {msg}: {e}")
        await asyncio.sleep(2)  # jeda aman antar pesan

# ---------------- REGEX ----------------
exp_re = re.compile(r"EXP[+ ]+(\d+)", re.IGNORECASE)
exp_status_re = re.compile(r"EXP:\s*([\d,]+)\/([\d,]+)", re.IGNORECASE)
maling_code_re = re.compile(r"(/curiuang_\d+)")

# ---------------- HANDLER PESAN BOT GAME ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def handler(event):
    global exp_current, exp_max
    text = event.raw_text or ""

    # Cek EXP dari pesan (EXP+)
    m_gain = exp_re.search(text)
    if m_gain:
        gain = int(m_gain.group(1))
        exp_current += gain
        if exp_max:
            exp_current = min(exp_current, exp_max)
            print(f"[EXP] +{gain} → {exp_current}/{exp_max}")
        else:
            print(f"[EXP] +{gain}")

    # Cek EXP status (EXP: x/y)
    m_status = exp_status_re.search(text)
    if m_status:
        exp_current = int(m_status.group(1).replace(",", ""))
        exp_max = int(m_status.group(2).replace(",", ""))
        print(f"[STATUS] EXP {exp_current}/{exp_max}")
        # Jika penuh → level up
        if exp_current >= exp_max:
            await safe_send("/levelup")

    # Cek kode maling
    if "uang" in text.lower():
        m_code = maling_code_re.search(text)
        if m_code and running_maling:
            code = m_code.group(1)
            print(f"[MALING] Kirim kode: {code}")
            await safe_send(code)

# ---------------- LOOP MALING ----------------
async def maling_loop():
    global running_maling
    while running_maling:
        await safe_send("/maling")
        await asyncio.sleep(random.randint(8, 12))  # jeda acak

# ---------------- LOOP KEBUN ----------------
async def kebun_loop():
    global running_kebun
    while running_kebun:
        print("[KEBUN] Tanam wortel")
        await safe_send("/tanam_Wortel_30")
        await asyncio.sleep(2)
        print("[KEBUN] Siram tanaman")
        await safe_send("/siram")
        # Tunggu 185 detik sampai panen
        print("[KEBUN] Menunggu 185 detik sampai panen...")
        await asyncio.sleep(185)
        print("[KEBUN] Panen")
        await safe_send("/ambilPanen")

# ---------------- OWNER COMMANDS ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def owner_cmd(event):
    global running_maling, running_kebun
    msg = event.raw_text.strip().lower()

    if msg == "start maling":
        if not running_maling:
            running_maling = True
            asyncio.create_task(maling_loop())
            await event.reply("▶️ MALING STARTED")
    elif msg == "stop maling":
        running_maling = False
        await event.reply("⏹ MALING STOPPED")

    elif msg == "start kebun":
        if not running_kebun:
            running_kebun = True
            asyncio.create_task(kebun_loop())
            await event.reply("▶️ KEBUN STARTED")
    elif msg == "stop kebun":
        running_kebun = False
        await event.reply("⏹ KEBUN STOPPED")

    elif msg == "start all":
        if not running_maling:
            running_maling = True
            asyncio.create_task(maling_loop())
        if not running_kebun:
            running_kebun = True
            asyncio.create_task(kebun_loop())
        await event.reply("▶️ ALL STARTED")

    elif msg == "stop all":
        running_maling = False
        running_kebun = False
        await event.reply("⏹ ALL STOPPED")

    elif msg == "status":
        await event.reply(f"[STATUS] EXP {exp_current}/{exp_max}")

# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    print(">> Bot siap jalan.")
    print("   Perintah: 'start maling' / 'stop maling'")
    print("             'start kebun'  / 'stop kebun'")
    print("             'start all'    / 'stop all'")
    print("             'status'")
    await safe_send("/status")  # cek status awal
    asyncio.create_task(message_worker())
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        while True:
            try:
                asyncio.run(main())
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print("!! Crash, restart 5s:", e)
                time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting.")
