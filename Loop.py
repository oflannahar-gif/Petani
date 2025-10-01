# auto_game.py — Auto Mancing & Masak di Kampung Maifam
# Features:
#   - 'Masak' → pilih menu, loop kirim kode masak tiap 2 detik
#   - 'Mancing' → pilih lokasi, loop kirim lokasi + klik "Tarik Alat Pancing"
#   - Pause/Resume/Stop manual
#   - Hentikan loop otomatis jika energi habis
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
logger = logging.getLogger("auto_game_bot")

# ---------------- client ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- state ----------------
mode = None  # "mancing" atau "masak"
lokasi_mancing = None
kode_masak = None
auto_loop = False
paused = False

async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- loop masak ----------------
async def loop_masak():
    global auto_loop, kode_masak, paused
    print(">> Loop Masak dimulai")
    while auto_loop and kode_masak:
        if paused:
            await asyncio.sleep(1)
            continue
        try:
            print(f">> Mengirim kode masak: {kode_masak}")
            await client.send_message(BOT_USERNAME, kode_masak)
            await asyncio.sleep(2)
        except Exception as e:
            print("❌ Error loop masak:", e)
            await asyncio.sleep(2)

# ---------------- loop mancing ----------------
async def loop_mancing():
    global auto_loop, lokasi_mancing, paused
    print(">> Loop Mancing dimulai")
    while auto_loop and lokasi_mancing:
        if paused:
            await asyncio.sleep(2)
            continue
        try:
            await client.send_message(BOT_USERNAME, lokasi_mancing)
            await asyncio.sleep(2)
        except Exception as e:
            print("❌ Error loop mancing:", e)
            await asyncio.sleep(3)

# ---------------- handler owner ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    global mode, lokasi_mancing, kode_masak, auto_loop, paused

    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()

    print(f">> INPUT OWNER: {msg}")

    if lmsg == "masak":
        mode = "masak"
        kode_masak = None
        auto_loop = False
        paused = False
        await event.reply("Mau Masak apa?")

    elif lmsg == "mancing":
        mode = "mancing"
        lokasi_mancing = None
        auto_loop = False
        paused = False
        await event.reply("Mancing dimana? 🎣")

    elif lmsg == "stop":
        auto_loop = False
        kode_masak = None
        lokasi_mancing = None
        paused = False
        mode = None
        await event.reply("⏹ Semua loop dihentikan")

    else:
        # input kode masak atau lokasi mancing
        if mode == "masak" and not kode_masak:
            kode_masak = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-masak: {kode_masak}")
            asyncio.create_task(loop_masak())

        elif mode == "mancing" and not lokasi_mancing:
            lokasi_mancing = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
            asyncio.create_task(loop_mancing())

# ---------------- handler bot game ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    global lokasi_mancing, kode_masak, auto_loop, paused, mode

    text = (event.raw_text or "").lower()
    print(f"[BOT] {text[:80]}...")

    # ====== DETEKSI ENERGI HABIS ======
    if "kamu tidak memiliki cukup energi" in text and "/tidur" in text:
        print("⚠️ Energi habis! Semua loop dihentikan.")
        auto_loop = False
        lokasi_mancing = None
        kode_masak = None
        paused = False
        mode = None
        return

    # ====== LOOP MANCING ======
    if mode == "mancing" and auto_loop and lokasi_mancing and not paused:
        # klik tombol "Tarik Alat Pancing" kalau ada
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in button.text:
                        await human_sleep()
                        await button.click()
                        print(">> Klik 'Tarik Alat Pancing'")
                        return
        # kirim ulang lokasi jika ada hasil tangkapan
        if "kamu mendapatkan" in text:
            await human_sleep(1, 2)
            await client.send_message(BOT_USERNAME, lokasi_mancing)
            print(f">> Kirim ulang lokasi: {lokasi_mancing}")

# ---------------- startup ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    msg_intro = ("Bot siap ✅\n\nCommand di Saved Messages:\n"
                 "- 'Masak' → pilih menu\n"
                 "- 'Mancing' → pilih lokasi\n"
                 "- 'stop' → hentikan loop")
    print(msg_intro)

    # Kirim ke Saved Messages
    try:
        await client.send_message("me", msg_intro)
        print(">> Pesan awal dikirim ke Saved Messages")
    except Exception as e:
        print("❌ Gagal kirim ke Saved Messages:", e)

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
