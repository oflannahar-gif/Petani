# auto_game.py — Auto Mancing, Masak & Grinding di Kampung Maifam
# Features:
#   - 'Masak' → pilih menu, loop kirim kode masak tiap 2 detik
#   - 'Mancing' → pilih lokasi, loop kirim lokasi + klik "Tarik Alat Pancing"
#   - 'Grinding' → kirim urutan tanam-siram-panen berulang sesuai jumlah input
#   - 'Macul' → otomatis tanam, siram, tunggu waktu panen dari tanaman.txt
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
mode = None  # "mancing" / "masak" / "grinding" / "macul"
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

# macul state
tanaman_data = {}  # {"Wortel":185, ...}
tanaman_dipilih = None
jumlah_tanam = 0
macul_loop = False

async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- load tanaman.txt ----------------
def load_tanaman():
    global tanaman_data
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

# ---------------- loop macul ----------------
async def loop_macul():
    global auto_loop, macul_loop, tanaman_dipilih, jumlah_tanam, paused
    waktu_tanam = tanaman_data.get(tanaman_dipilih, 180)
    print(f">> Mulai auto macul: {tanaman_dipilih} ({jumlah_tanam} pohon, {waktu_tanam}s)")
    await client.send_message(OWNER_ID, f"🌱 Mulai auto Macul: {tanaman_dipilih} ({jumlah_tanam} pohon, {waktu_tanam}s)")

    while auto_loop and macul_loop:
        if paused:
            await asyncio.sleep(1)
            continue

        try:
            cmd_tanam = f"/tanam_{tanaman_dipilih}_{jumlah_tanam}"
            print(f">> Tanam: {cmd_tanam}")
            await client.send_message(BOT_USERNAME, cmd_tanam)
            await asyncio.sleep(2)

            print(">> Siram")
            await client.send_message(BOT_USERNAME, "/siram")
            await asyncio.sleep(waktu_tanam)  # waktu tunggu panen

            print(">> Panen")
            await client.send_message(BOT_USERNAME, "/ambilPanen")
            await asyncio.sleep(3)  # 🌾 jeda 3 detik sebelum mulai tanam lagi

        except Exception as e:
            print("❌ Error loop macul:", e)

        await asyncio.sleep(2)

# ---------------- handler owner ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    global mode, lokasi_mancing, kode_masak, auto_loop, paused
    global grinding_loops, tanaman_dipilih, jumlah_tanam, macul_loop

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

    elif lmsg == "macul":
        mode = "macul"
        tanaman_dipilih = None
        jumlah_tanam = 0
        macul_loop = False
        auto_loop = False
        paused = False
        load_tanaman()
        await event.reply("🌱 Mau tanam apa?")

    elif lmsg == "stop":
        auto_loop = False
        macul_loop = False
        kode_masak = None
        lokasi_mancing = None
        paused = False
        mode = None
        await event.reply("⏹ Semua loop dihentikan")

    else:
        # mode masak
        if mode == "masak" and not kode_masak:
            kode_masak = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-masak: {kode_masak}")
            asyncio.create_task(loop_masak())

        # mode mancing
        elif mode == "mancing" and not lokasi_mancing:
            lokasi_mancing = msg
            auto_loop = True
            paused = False
            await event.reply(f"Mulai auto-mancing di {lokasi_mancing} 🎣")
            await human_sleep()
            await client.send_message(BOT_USERNAME, lokasi_mancing)

        # mode grinding
        elif mode == "grinding" and grinding_loops == 0:
            if msg.isdigit():
                grinding_loops = int(msg)
                auto_loop = True
                paused = False
                await event.reply(f"Mulai grinding sebanyak {grinding_loops}x siklus 🔄")
                asyncio.create_task(loop_grinding())
            else:
                await event.reply("❗ Masukkan angka jumlah loop grinding.")

        # mode macul
        elif mode == "macul":
            # pilih tanaman
            if not tanaman_dipilih:
                if msg in tanaman_data:
                    tanaman_dipilih = msg
                    await event.reply(f"Berapa jumlah {tanaman_dipilih} yang mau ditanam?")
                else:
                    await event.reply("🌾 Tanaman tidak ditemukan di file tanaman.txt.")
            elif jumlah_tanam == 0:
                if msg.isdigit():
                    jumlah_tanam = int(msg)
                    auto_loop = True
                    macul_loop = True
                    paused = False
                    await event.reply(f"Mulai Macul otomatis {tanaman_dipilih} ({jumlah_tanam} pohon).")
                    asyncio.create_task(loop_macul())
                else:
                    await event.reply("Masukkan angka jumlah tanaman yang valid.")

# ---------------- handler bot game ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    global lokasi_mancing, kode_masak, auto_loop, paused, mode, macul_loop

    text = event.raw_text or ""
    print(f"[BOT] {text[:60]}...")

    if "kamu tidak memiliki cukup energi" in text.lower() and "/tidur" in text.lower():
        print("⚠️ Energi habis! Semua loop dihentikan.")
        auto_loop = False
        macul_loop = False
        kode_masak = None
        lokasi_mancing = None
        paused = False
        mode = None
        await client.send_message(OWNER_ID, "⚠️ Energi habis! Loop otomatis dihentikan.")
        return

    if mode == "mancing" and auto_loop and lokasi_mancing and not paused:
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in button.text:
                        await human_sleep()
                        await button.click()
                        print(">> Klik 'Tarik Alat Pancing'")
                        return
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
                 "- 'Macul' → otomatis tanam, siram, tunggu panen dari tanaman.txt\n"
                 "- 'stop' → hentikan loop")
    print(msg_intro)
    try:
        await client.send_message("me", msg_intro)
        print(">> Pesan awal dikirim ke Saved Messages")
    except Exception as e:
        print("❌ Gagal kirim ke Saved Messages:", e)

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
