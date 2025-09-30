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
running = False
last_sent = {}  # {kode: timestamp}
DELAY_BETWEEN_CODES = 120   # 2 menit
DELAY_REPEAT_CODE = 3600    # 1 jam


# --- Baca codes.txt ---
def load_codes():
    with open("codes.txt", "r") as f:
        codes = [line.strip() for line in f if line.strip()]
    return codes


# --- Task pengiriman otomatis ---
async def auto_send():
    global running
    while True:
        if running:
            codes = load_codes()
            for code in codes:
                now = time.time()
                last_time = last_sent.get(code, 0)

                if now - last_time >= DELAY_REPEAT_CODE:
                    try:
                        await client.send_message(BOT_USERNAME, code)
                        print(f"[+] Terkirim: {code}")
                        last_sent[code] = now
                    except Exception as e:
                        print(f"[!] Gagal kirim {code}: {e}")
                    await asyncio.sleep(DELAY_BETWEEN_CODES)
                else:
                    # Lewati kode yang belum 1 jam
                    continue
        else:
            await asyncio.sleep(5)  # kalau stop, tunggu sebentar


# --- Handler perintah dari Saved Messages ---
@client.on(events.NewMessage(chats=OWNER_ID))
async def handler(event):
    global running
    msg = event.raw_text.lower().strip()

    if msg == "start":
        running = True
        await event.reply("✅ Auto-sender DIMULAI")
        print(">> Auto-sender STARTED")

    elif msg == "stop":
        running = False
        await event.reply("⏹ Auto-sender DIHENTIKAN")
        print(">> Auto-sender STOPPED")


# --- Main ---
async def main():
    print(">> Bot siap jalan. Kirim 'start' atau 'stop' di Saved Messages kamu.")
    asyncio.create_task(auto_send())  # jalankan loop auto_send
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
