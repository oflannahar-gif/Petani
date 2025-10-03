# auto_game.py — Auto Mancing, Masak & Grinding di Kampung Maifam
# Features:
#   - 'Masak' → pilih menu, loop kirim kode masak tiap 2 detik
#   - 'Mancing' → pilih lokasi, loop kirim lokasi + klik "Tarik Alat Pancing"
#   - 'Grinding' → kirim urutan tanam-siram-panen berulang sesuai jumlah input
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
mode = None  # "mancing" atau "masak" atau "grinding"
lokasi_mancing = None
kode_masak = None
auto_loop = False
paused = False

# grinding state
grinding_loops = 0
grinding_count = 0
grinding_sequence = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

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

# ---------------- loop grinding ----------------
async def loop_grinding():
    global auto_loop, grinding_loops, grinding_count, paused
    print(f">> Loop Grinding dimulai ({grinding_loops}x siklus)")
    grinding_count = 0

    while auto_loop and grinding_count < grinding_loops:
        if paused:
            await asyncio.sleep(1)
            continue
        try:
            for cmd in grinding_sequence:
                if not auto_loop:
                    break
                print(f">> [Grinding {grinding_count+1}/{grinding_loops}] Kirim: {cmd}")
                await client.send_message(BOT_USERNAME, cmd)
                await asyncio.sleep(2)
            grinding_count += 1
        except Exception as e:
            print("❌ Error loop grinding:", e)
            await asyncio.sleep(2)

    if grinding_count >= grinding_loops:
        auto_loop = False
        await client.send_message(OWNER_ID, f"✅ Grinding selesai ({grinding_loops}x siklus)")
        print(f">> Grinding selesai ({grinding_loops}x siklus)")

# ---------------- handler owner ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    global mode, lokasi_mancing, kode_masak, auto_loop, paused, grinding_loops

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

    elif lmsg == "grinding":
        mode = "grinding"
        grinding_loops = 0
        auto_loop = False
        paused = False
        await event.reply("Mau berapa kali grinding? 🔄")

    elif lmsg == "stop":
        auto_loop = False
        kode_masak = None
        lokasi_mancing = None
        paused = False
        mode = None
        await event.reply("⏹ Semua loop dihentikan")

    else:
        # input kode masak
        if mode == "masak" and not kode_masak:
            kode_masak = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-masak: {kode_masak}")
            asyncio.create_task(loop_masak())

        # input lokasi mancing
        elif mode == "mancing" and not lokasi_mancing:
            lokasi_mancing = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
            await human_sleep()
            await client.send_message(BOT_USERNAME, lokasi_mancing)

        # input jumlah grinding
        elif mode == "grinding" and grinding_loops == 0:
            if msg.isdigit():
                grinding_loops = int(msg)
                auto_loop = True
                paused = False
                await event.reply(f"Mulai grinding sebanyak {grinding_loops}x siklus 🔄")
                asyncio.create_task(loop_grinding())
            else:
                await event.reply("❗ Masukkan angka jumlah loop grinding.")

# ---------------- handler bot game ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    global lokasi_mancing, kode_masak, auto_loop, paused, mode

    text = event.raw_text or ""
    print(f"[BOT] {text[:60]}...")

    # ====== DETEKSI ENERGI HABIS ======
    if "kamu tidak memiliki cukup energi" in text.lower() and "/tidur" in text.lower():
        print("⚠️ Energi habis! Semua loop dihentikan.")
        auto_loop = False
        kode_masak = None
        lokasi_mancing = None
        paused = False
        mode = None
        await client.send_message(OWNER_ID, "⚠️ Energi habis! Loop otomatis dihentikan.")
        return

    # klik tombol "Tarik Alat Pancing" kalau ada
    if mode == "mancing" and auto_loop and lokasi_mancing and not paused:
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in button.text:
                        await human_sleep()
                        await button.click()
                        print(">> Klik 'Tarik Alat Pancing'")
                        return

        # kalau ada hasil tangkapan, kirim ulang lokasi
        if "kamu mendapatkan" in text.lower():
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
                 "- 'Grinding' → tanam+siram+panen berulang\n"
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
