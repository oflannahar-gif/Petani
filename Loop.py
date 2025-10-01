# auto_game.py — Auto Fishing & Cooking di Kampung Maifam
# Features:
#   - Mode Mancing: pilih lokasi → auto klik "Tarik Alat Pancing" + ulang
#   - Mode Masak: pilih resep → loop kirim kode resep tiap 2 detik
#   - Pause / Resume / Stop manual
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
logger = logging.getLogger("game_bot")

# ---------------- client ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- state ----------------
mode = None           # None, "mancing", "masak"
auto_loop = False
paused = False
lokasi_mancing = None
kode_masak = None
waiting_input = False  # menandai kalau bot menunggu input user

async def human_sleep(min_s=1.0, max_s=1.5):
    """Jeda random biar ga terlalu bot-like"""
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- commands ----------------
@client.on(events.NewMessage(from_users=OWNER_ID, pattern='mancing'))
async def cmd_mancing(event):
    global mode, auto_loop, lokasi_mancing, kode_masak, waiting_input
    mode = "mancing"
    lokasi_mancing = None
    kode_masak = None
    auto_loop = False
    waiting_input = True
    await event.reply("Mancing dimana? 🎣")

@client.on(events.NewMessage(from_users=OWNER_ID, pattern='masak'))
async def cmd_masak(event):
    global mode, auto_loop, lokasi_mancing, kode_masak, waiting_input
    mode = "masak"
    lokasi_mancing = None
    kode_masak = None
    auto_loop = False
    waiting_input = True
    await event.reply("Mau masak apa? 🍳 (contoh: /masak_udangkeju_40)")

@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    global auto_loop, lokasi_mancing, kode_masak, paused, mode, waiting_input
    msg = (event.raw_text or "").strip()

    # kontrol umum
    if msg.lower() == "pause":
        paused = True
        await event.reply("⏸ Loop dijeda")
        return
    elif msg.lower() == "resume":
        paused = False
        await event.reply("▶️ Loop dilanjutkan")
        # kirim lokasi mascing kalau perlu resume
        if mode == "mancing" and lokasi_mancing:
            await human_sleep()
            await client.send_message(BOT_USERNAME, lokasi_mancing)
        return
    elif msg.lower() == "stop":
        auto_loop = False
        lokasi_mancing = None
        kode_masak = None
        mode = None
        paused = False
        waiting_input = False
        await event.reply("⏹ Loop dihentikan")
        return

    # input user ketika menunggu
    if waiting_input:
        if mode == "mancing":
            lokasi_mancing = msg
            auto_loop = True
            paused = False
            waiting_input = False
            await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
            await human_sleep()
            await client.send_message(BOT_USERNAME, lokasi_mancing)
        elif mode == "masak":
            kode_masak = msg
            auto_loop = True
            paused = False
            waiting_input = False
            await event.reply(f"Mulai auto-masak dengan kode {kode_masak} 🍳")
            asyncio.create_task(loop_masak())

# ---------------- handler untuk bot game (Mancing) ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    global auto_loop, lokasi_mancing, paused, mode
    if not auto_loop or paused or mode != "mancing" or not lokasi_mancing:
        return

    text = event.raw_text or ""
    print(f"[BOT] {text[:60]}...")

    # klik tombol kalau ada
    if event.buttons:
        for row in event.buttons:
            for button in row:
                if "Tarik Alat Pancing" in button.text:
                    await human_sleep()
                    await button.click()
                    return

    # kalau ada hasil tangkapan, kirim ulang lokasi
    if "kamu mendapatkan" in text.lower():
        await human_sleep(1, 2)
        await client.send_message(BOT_USERNAME, lokasi_mancing)

# ---------------- loop masak ----------------
async def loop_masak():
    global auto_loop, kode_masak, paused, mode
    while auto_loop and kode_masak and mode == "masak":
        if not paused:
            await client.send_message(BOT_USERNAME, kode_masak)
        await asyncio.sleep(2)

# ---------------- startup ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    print(f">> Bot siap Auto Game di @{BOT_USERNAME}")

    # kirim pesan ke Saved Messages
    await client.send_message(
        OWNER_ID,
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- 'Masak' → pilih menu\n"
        "- 'Mancing' → pilih lokasi\n"
        "- 'stop' → hentikan loop"
    )

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
