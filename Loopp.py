# auto_game_multi.py — Auto Mancing, Masak, Macul & Grinding (Multi-loop Support)
# Features:
#   - Multi-loop aktif (semua fitur bisa jalan bersamaan)
#   - Queue aman untuk pengiriman pesan
#   - Stop per fitur & stop all
#   - Energi habis → hentikan semua loop otomatis
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

# ---------------- CONFIG (.env) ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "KampungMaifamBot").lstrip('@')
OWNER_ID = int(os.getenv("OWNER_ID") or 0)

if not API_ID or not API_HASH or not PHONE:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE ter-set di kunci.env")

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("auto_game_bot")

# ---------------- CLIENT ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- QUEUE SYSTEM ----------------
message_queue = asyncio.Queue()

async def safe_send(msg, to=None):
    await message_queue.put((msg, to or BOT_USERNAME))

async def message_worker():
    while True:
        msg, dest = await message_queue.get()
        try:
            await client.send_message(dest, msg)
            print(f"[SEND] → {dest}: {msg}")
        except Exception as e:
            print(f"[!] Gagal kirim {msg} ke {dest}: {e}")
        await asyncio.sleep(2)

# ---------------- STATE FLAGS (Multi-loop) ----------------
is_masak = False
is_mancing = False
is_grinding = False
is_macul = False

paused = False

lokasi_mancing = None
kode_masak = None

grinding_loops = 0
grinding_count = 0
grinding_sequence = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

tanaman_data = {}
tanaman_dipilih = None
jumlah_tanam = 0

# ---------------- UTIL ----------------
async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

def load_tanaman():
    tanaman_data.clear()
    if not os.path.exists("tanaman.txt"):
        print("⚠️ File tanaman.txt tidak ditemukan.")
        return
    with open("tanaman.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                nama, waktu = line.strip().split("=")
                try:
                    tanaman_data[nama.strip()] = int(waktu.strip())
                except ValueError:
                    continue
    print(f"🌿 {len(tanaman_data)} tanaman dimuat: {', '.join(tanaman_data.keys())}")

# ---------------- LOOP FUNCTIONS ----------------
async def loop_masak():
    global is_masak, kode_masak
    print(">> Loop Masak dimulai")
    while is_masak and kode_masak:
        if paused:
            await asyncio.sleep(1)
            continue
        await safe_send(kode_masak)
        print(f">> Kirim masak: {kode_masak}")
        await asyncio.sleep(2)
    print("🍳 Loop Masak berhenti")

async def loop_grinding():
    global is_grinding, grinding_loops, grinding_count
    print(f">> Loop Grinding dimulai ({grinding_loops}x siklus)")
    grinding_count = 0
    while is_grinding and grinding_count < grinding_loops:
        if paused:
            await asyncio.sleep(1)
            continue
        for cmd in grinding_sequence:
            if not is_grinding:
                break
            await safe_send(cmd)
            print(f">> Grinding {grinding_count+1}/{grinding_loops}: {cmd}")
            await asyncio.sleep(2)
        grinding_count += 1
    print("⚙️ Grinding selesai")
    await safe_send(f"✅ Grinding selesai ({grinding_loops}x siklus)", OWNER_ID)
    is_grinding = False

async def loop_macul():
    global is_macul, tanaman_dipilih, jumlah_tanam
    waktu_tanam = tanaman_data.get(tanaman_dipilih, 180)
    print(f">> Mulai Macul: {tanaman_dipilih} ({jumlah_tanam}, {waktu_tanam}s)")
    while is_macul:
        if paused:
            await asyncio.sleep(1)
            continue
        try:
            await safe_send(f"/tanam_{tanaman_dipilih}_{jumlah_tanam}")
            await asyncio.sleep(2)
            await safe_send("/siram")
            await asyncio.sleep(waktu_tanam)
            await safe_send("/ambilPanen")
            await asyncio.sleep(3)
        except Exception as e:
            print("❌ Error loop macul:", e)
    print("🌾 Loop Macul berhenti")

# ---------------- HANDLER OWNER ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def owner_cmd(event):
    global is_masak, is_mancing, is_grinding, is_macul
    global kode_masak, lokasi_mancing, grinding_loops, tanaman_dipilih, jumlah_tanam

    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()

    print(f">> CMD: {msg}")

    # ---- START COMMAND ----
    if lmsg == "masak":
        is_masak = False
        kode_masak = None
        await event.reply("Mau Masak apa?")

    elif lmsg == "mancing":
        is_mancing = False
        lokasi_mancing = None
        await event.reply("Mancing dimana? 🎣")

    elif lmsg == "grinding":
        is_grinding = False
        grinding_loops = 0
        await event.reply("Mau berapa kali grinding? 🔄")

    elif lmsg == "macul":
        load_tanaman()
        is_macul = False
        tanaman_dipilih = None
        jumlah_tanam = 0
        await event.reply("🌱 Mau tanam apa?")

    # ---- STOP COMMAND ----
    elif lmsg in ("stop", "stop_all"):
        is_masak = is_mancing = is_grinding = is_macul = False
        await event.reply("⏹ Semua loop dihentikan.")

    elif lmsg == "stop_masak":
        is_masak = False
        await event.reply("🍳 Loop Masak dihentikan.")

    elif lmsg == "stop_mancing":
        is_mancing = False
        await event.reply("🎣 Loop Mancing dihentikan.")

    elif lmsg == "stop_grinding":
        is_grinding = False
        await event.reply("⚙️ Loop Grinding dihentikan.")

    elif lmsg == "stop_macul":
        is_macul = False
        await event.reply("🌾 Loop Macul dihentikan.")

    # ---- MODE INPUT ----
    else:
        # Masak
        if kode_masak is None and not is_mancing and not is_grinding and not is_macul and msg.startswith("/"):
            kode_masak = msg
            is_masak = True
            await event.reply(f"Mulai auto-masak: {kode_masak}")
            asyncio.create_task(loop_masak())

        # Mancing
        elif not lokasi_mancing and not is_grinding and not is_macul and not msg.startswith("/"):
            if lmsg.startswith("danau") or lmsg.startswith("laut") or lmsg.startswith("kolam"):
                lokasi_mancing = msg
                is_mancing = True
                await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
                await safe_send(lokasi_mancing)
            else:
                pass

        # Grinding
        elif is_grinding == False and grinding_loops == 0 and msg.isdigit():
            grinding_loops = int(msg)
            is_grinding = True
            await event.reply(f"Mulai grinding sebanyak {grinding_loops}x siklus 🔄")
            asyncio.create_task(loop_grinding())

        # Macul
        elif tanaman_dipilih is None and msg in tanaman_data:
            tanaman_dipilih = msg
            await event.reply(f"Berapa jumlah {tanaman_dipilih} yang mau ditanam?")
        elif tanaman_dipilih and jumlah_tanam == 0 and msg.isdigit():
            jumlah_tanam = int(msg)
            is_macul = True
            await event.reply(f"Mulai Macul otomatis {tanaman_dipilih} ({jumlah_tanam} pohon).")
            asyncio.create_task(loop_macul())

# ---------------- HANDLER GAME BOT ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    global is_mancing, lokasi_mancing, is_masak, is_macul, is_grinding

    text = event.raw_text or ""
    if "tidak memiliki cukup energi" in text.lower():
        is_mancing = is_masak = is_grinding = is_macul = False
        await safe_send("⚠️ Energi habis! Semua loop dihentikan.", OWNER_ID)
        return

    # Auto klik "Tarik Alat Pancing"
    if is_mancing and event.buttons:
        for row in event.buttons:
            for btn in row:
                if "Tarik Alat Pancing" in btn.text:
                    await human_sleep()
                    await btn.click()
                    print("🎣 Klik 'Tarik Alat Pancing'")
                    return

    if is_mancing and "kamu mendapatkan" in text.lower():
        await human_sleep(1, 2)
        await safe_send(lokasi_mancing)

# ---------------- STARTUP ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    asyncio.create_task(message_worker())

    msg_intro = (
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- 'Masak' → pilih menu\n"
        "- 'Mancing' → pilih lokasi\n"
        "- 'Grinding' → tanam+siram+panen berulang\n"
        "- 'Macul' → otomatis tanam, siram, tunggu panen dari tanaman.txt\n"
        "- 'stop' → hentikan loop\n"
        "- 'stop_all' → hentikan semua loop"
    )
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
