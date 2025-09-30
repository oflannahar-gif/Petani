import os
import asyncio
import time
from telethon import TelegramClient, events
from dotenv import load_dotenv

# --- Load data dari .env ---
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # target bot
OWNER_ID = int(os.getenv("OWNER_ID"))

# --- Inisialisasi Telethon ---
client = TelegramClient("Petani_session", API_ID, API_HASH)

# --- Variabel kontrol ---
running_maling = False
running_kebun = False
last_sent = {}  # {kode: timestamp}

# Delay aturan maling
DELAY_BETWEEN_CODES = 120   # 2 menit
DELAY_REPEAT_CODE = 3600    # 1 jam

# Delay aturan kebun
DELAY_AFTER_TANAM = 2       # 2 detik
DELAY_AFTER_SIRAM = 185     # 3 menit 5 detik
DELAY_AFTER_PANEN = 2       # 2 detik


# --- Baca codes.txt ---
def load_codes():
    with open("codes.txt", "r") as f:
        codes = [line.strip() for line in f if line.strip()]
    return codes


# --- Task pengiriman otomatis (Maling) ---
async def auto_maling():
    global running_maling
    while True:
        if running_maling:
            codes = load_codes()
            for code in codes:
                now = time.time()
                last_time = last_sent.get(code, 0)

                if now - last_time >= DELAY_REPEAT_CODE:
                    try:
                        await client.send_message(BOT_USERNAME, code)
                        print(f"[MALING] [+] Terkirim: {code}")
                        last_sent[code] = now
                    except Exception as e:
                        print(f"[MALING] [!] Gagal kirim {code}: {e}")
                    await asyncio.sleep(DELAY_BETWEEN_CODES)
                else:
                    continue
        else:
            await asyncio.sleep(5)


# --- Task Kebun (Wortel) ---
async def auto_kebun():
    global running_kebun
    while True:
        if running_kebun:
            try:
                # Tanam
                await client.send_message(BOT_USERNAME, "/tanam_Wortel_25")
                print("[KEBUN] Tanam Wortel")
                await asyncio.sleep(DELAY_AFTER_TANAM)

                # Siram
                await client.send_message(BOT_USERNAME, "/siram")
                print("[KEBUN] Siram Wortel")
                await asyncio.sleep(DELAY_AFTER_SIRAM)

                # Panen
                await client.send_message(BOT_USERNAME, "/ambilPanen")
                print("[KEBUN] Panen Wortel")
                await asyncio.sleep(DELAY_AFTER_PANEN)

            except Exception as e:
                print(f"[KEBUN] [!] Gagal aksi kebun: {e}")
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(5)


# --- Handler perintah dari Saved Messages ---
@client.on(events.NewMessage(chats=OWNER_ID))
async def handler(event):
    global running_maling, running_kebun
    msg = event.raw_text.lower().strip()

    if msg == "start maling":
        running_maling = True
        await event.reply("✅ Loop Maling DIMULAI")
        print(">> Loop maling STARTED")

    elif msg == "stop maling":
        running_maling = False
        await event.reply("⏹ Loop Maling DIHENTIKAN")
        print(">> Loop maling STOPPED")

    elif msg == "start kebun":
        running_kebun = True
        await event.reply("✅ Loop Kebun DIMULAI")
        print(">> Loop kebun STARTED")

    elif msg == "stop kebun":
        running_kebun = False
        await event.reply("⏹ Loop Kebun DIHENTIKAN")
        print(">> Loop kebun STOPPED")

    elif msg == "stop all":
        running_maling = False
        running_kebun = False
        await event.reply("⏹ Semua loop dihentikan")
        print(">> Semua loop STOPPED")


# --- Main ---
async def main():
    print(">> Bot siap jalan.")
    print("Ketik 'start maling' atau 'start kebun' di Saved Messages kamu.")
    asyncio.create_task(auto_maling())
    asyncio.create_task(auto_kebun())
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
